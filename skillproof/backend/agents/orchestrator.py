import threading
import uuid
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import config
from agents import planner,repository_agent,code_agent,test_agent,git_agent,originality_agent,skill_evaluator,viva_generator
from database import repositories as memory
from core.state_machine import transition
from core.exceptions import AppError
from core.logging import logger
from services.evidence_service import attach_results,implementation_evidence
from services.scoring_service import calculate
from tools.dependency_tool import relationships
from services.provenance_service import freeze_baseline,enrich_evidence
from rag.vector_store import index_repository as rag_index_repo, get_chunks_count
from rag.retriever import retrieve_for_skill, chunks_to_evidence_items

locks = defaultdict(threading.RLock)
executor = ThreadPoolExecutor(max_workers=2,thread_name_prefix='skillproof')
scheduled = set()
schedule_lock = threading.Lock()

def submit(sid):
    with schedule_lock:
        if sid in scheduled:
            return
        if len(scheduled)>=20:
            raise AppError('Analysis queue full',503,'QUEUE_FULL')
        scheduled.add(sid)
    def worker():
        try:
            run(sid)
        finally:
            with schedule_lock:
                scheduled.discard(sid)
    executor.submit(worker)

def recover():
    for sid in memory.pending():
        submit(sid)

def llm(data,agent,phase,fn,*args):
    check_budget(data)
    from urllib.parse import urlsplit
    memory.record(data,agent,phase,{'provider_host':urlsplit(config.LLM_BASE_URL).hostname,'model':config.LLM_MODEL},'started')
    try:
        result=fn(*args)
    except AppError as exc:
        memory.record(data,agent,phase,{'error_code':exc.code,'message':exc.message},'failed')
        raise
    data['llm_calls']+=1
    memory.record(data,agent,phase,{'validated_response':result})
    return result

def check_budget(data):
    if data['current_status'] in {'PLANNING','ANALYSING','TESTING','EVALUATING'} and time.time()>data.get('_deadline',float('inf')):
        data['stop_reason']='TIME_BUDGET_EXCEEDED'
        raise AppError('Investigation time budget exceeded; collected evidence preserved',409,'TIME_BUDGET_EXCEEDED')

def tool(data,name,fn,*args):
    check_budget(data)
    execution={'execution_id':str(uuid.uuid4()),'tool':name,'started_at':memory.now(),'status':'started'}
    memory.record(data,name,'ACT',execution,'started',events=[('tool_executions',execution)])
    try:
        result=fn(*args)
    except Exception:
        execution.update(status='failed',finished_at=memory.now())
        memory.record(data,name,'OBSERVE',execution,'failed',events=[('tool_executions',execution)])
        raise
    execution.update(status='completed',finished_at=memory.now())
    memory.record(data,name,'OBSERVE',execution,events=[('tool_executions',execution)])
    return result

def merge(data,evidence,edges):
    by_id={e['evidence_id']:e for e in data['code_evidence']}
    by_id.update({e['evidence_id']:e for e in evidence})
    data['code_evidence']=list(by_id.values())
    all_edges=data['evidence_graph']+edges
    data['evidence_graph']=list({(e['source'],e['target'],e['relation']):e for e in all_edges}.values())

def run(sid):
    with locks[sid]:
        data=memory.get(sid)
        checkpoint=data['_checkpoint']
        data.setdefault('_deadline',time.time()+config.AGENT_BUDGET_SECONDS)
        data.setdefault('agent_cycles',[])
        try:
            if data['current_status']=='QUEUED':
                transition(data,'PLANNING')
                memory.save(data)
            if checkpoint.get('repository'):
                root,files,snapshot=repository_agent.resume(Path(data['_workspace']),data['github_url'],data['repository_commit_sha'])
                original_hashes=data['repository_snapshot'].get('file_hashes',{})
                if original_hashes and original_hashes!=snapshot['file_hashes']:
                    raise AppError('Pinned workspace file contents changed; refusing resume',409,'SNAPSHOT_CHANGED')
            else:
                # A new attempt directory avoids deleting partially cloned or historical snapshots.
                workspace=sid+'-'+uuid.uuid4().hex[:8]
                root,files,snapshot=tool(data,'repository',repository_agent.run,data['github_url'],workspace,data.get('_requested_sha'))
                data.update(repository_snapshot=snapshot,repository_commit_sha=snapshot['commit_sha'],_workspace=str(root))
                checkpoint['repository']=True
                memory.save(data,[('repository_snapshots',snapshot),('repository_files',list(files))])
            sha=data['repository_commit_sha']
            # Deterministic evidence acquisition precedes model use, so missing API keys cannot erase the baseline.
            if not checkpoint.get('baseline'):
                evidence,edges=tool(data,'source_baseline',code_agent.inspect,files,sha)
                merge(data,evidence,edges)
                data['_source_collected_at']=memory.now()
                enrich_evidence(data)
                data['commit_summary']=tool(data,'git',git_agent.run,root,sha)
                data['similarity_findings']=tool(data,'originality',originality_agent.run,files)
                data['test_results']=tool(data,'sandbox_tests',test_agent.run,root,files,data['evidence_graph'])
                checkpoint['tests']=True
                checkpoint['baseline']=True
                memory.save(data,[('git_findings',data['commit_summary']),('test_results',data['test_results']),('skill_evidence',evidence),('similarity_findings',data['similarity_findings'])])
                data['baseline']=freeze_baseline(data)
                memory.save(data)
            if not checkpoint.get('rag'):
                tool(data,'rag_indexer',rag_index_repo,sid,sha,files)
                rag_evidence={}
                for skill in data['claimed_skills']:
                    chunks=retrieve_for_skill(sid,sha,skill,top_k=2)
                    rag_evidence[skill]=chunks
                checkpoint['rag']=True
                data['rag_indexed']=True
                data['rag_chunks_count']=get_chunks_count(sid,sha)
                data['rag_evidence']=rag_evidence
                memory.save(data)
            if not checkpoint.get('plan'):
                data['analysis_plan']=llm(data,'planner','PLAN',planner.plan,{'url':data['github_url'],'skills':data['claimed_skills'],
                    'baseline':data.get('baseline'),'inventory':list(files),'evidence':skill_evaluator.compact(data['code_evidence'])})
                checkpoint['plan']=True
                memory.save(data,[('agent_plans',data['analysis_plan'])])
            if data['current_status']=='PLANNING':
                transition(data,'ANALYSING')
                memory.save(data)
            if not checkpoint.get('initial'):
                execute_cycle(data,root,files,sha,data['analysis_plan'],1)
                data['investigation_cycles']=1
                checkpoint['initial']=True
                memory.save(data)
            while data['investigation_cycles']<config.MAX_CYCLES and not checkpoint.get('investigation_done'):
                next_plan=llm(data,'planner','CRITIQUE',planner.critique,{'skills':data['claimed_skills'],
                    'inventory':list(files),'evidence':skill_evaluator.compact(data['code_evidence']),
                    'relationships':data['evidence_graph'][:100],'previous_gaps':data['missing_evidence'],'cycle':data['investigation_cycles']})
                data['missing_evidence']=next_plan['missing_evidence']
                memory.record(data,'planner','RE-PLAN',next_plan,events=[('agent_plans',next_plan)])
                memory.record(data,'planner','REFLECT',{'decision_summary':next_plan['rationale'],'missing_evidence':next_plan['missing_evidence']})
                if next_plan['stop'] or not next_plan['actions']:
                    checkpoint['investigation_done']=True
                    data['stop_reason']='EVIDENCE_SUFFICIENT' if not next_plan['missing_evidence'] else 'NO_USEFUL_ACTIONS'
                    data['agent_cycles'][-1]['replanning_decision']=next_plan['rationale']
                    data['agent_cycles'][-1]['stop_reason']=data['stop_reason']
                    memory.save(data)
                    break
                execute_cycle(data,root,files,sha,next_plan,data['investigation_cycles']+1)
                data['investigation_cycles']+=1
                memory.save(data)
            data['stop_reason']=data.get('stop_reason') or 'INVESTIGATION_BUDGET_EXHAUSTED'
            if data['agent_cycles']:
                data['agent_cycles'][-1]['stop_reason']=data['stop_reason']
            if data['current_status']=='ANALYSING':
                transition(data,'TESTING')
                memory.save(data)
            if not checkpoint.get('tests'):
                transition(data,'TESTING')
                memory.save(data)
                # Link discovered tests to inspected evidence across the actual full inventory.
                links=relationships(files,data['code_evidence'])
                merge(data,[],links)
                for item in data['code_evidence']:
                    item['test_references']=sorted({e['source'] for e in links if e['relation']=='TEST_IMPORTS' and e['target']==item['file']})
                data['test_results']=tool(data,'sandbox_tests',test_agent.run,root,files,data['evidence_graph'])
                attach_results(data['code_evidence'],data['test_results'])
                checkpoint['tests']=True
                memory.save(data,[('test_results',data['test_results'])])
            if data['current_status']=='TESTING':
                transition(data,'EVALUATING')
                memory.save(data)
            if not checkpoint.get('assessment'):
                data['assessments']=llm(data,'skill_evaluator','VERIFY',skill_evaluator.run,data['claimed_skills'],data['code_evidence'],data['evidence_graph'],data['test_results'],data['commit_summary'])
                checkpoint['assessment']=True
                memory.save(data,[('skill_evidence',data['assessments'])])
                enrich_evidence(data)
                for assessment in data['assessments']:
                    for ref in set(assessment['supporting_evidence']):
                        merge(data,[],[{'source':'skill:'+assessment['skill'],'target':ref,'relation':'SUPPORTED_BY','file':next((e['file'] for e in data['code_evidence'] if e['evidence_id']==ref),''),'line':None,'resolution':'model_interpretation_validated_citation'}])
            if not any(e['kind']!='documentation' and e['source'].strip() for e in data['code_evidence']):
                raise AppError('Insufficient production implementation evidence; viva and issuance blocked',409,'INSUFFICIENT_EVIDENCE')
            if not checkpoint.get('questions'):
                data['viva_questions']=llm(data,'viva_generator','VERIFY',viva_generator.run,data['code_evidence'])
                for q in data['viva_questions']:
                    item=next(e for e in data['code_evidence'] if e['evidence_id']==q['evidence_reference'])
                    q.update(line_start=item['line_start'],line_end=item['line_end'],related_evidence_ids=[item['evidence_id']],skill=next(iter(item.get('claimed_skills',[])),None))
                checkpoint['questions']=True
                memory.save(data,[('viva_questions',data['viva_questions'])])
            checkpoint['analysis_complete']=True
            data['limitations']=['Repository evidence does not establish candidate identity or personal authorship.',
                'This assessment evaluates available evidence, not the candidate\'s entire professional capability.',
                'Test definitions are not executed tests or coverage; inspect the independent execution status.',
                'Static call graph is partial; dynamic dispatch and all data flow are not resolved.',
                'No internet-wide plagiarism or reliable AI-authorship detection is performed.']
            if data.get('resume_info') and data['resume_info'].get('extracted_skills'):
                from services.resume_service import match_resume_to_repository
                data['resume_verification'] = match_resume_to_repository(
                    data['resume_info']['extracted_skills'],
                    data.get('code_evidence', []),
                    data.get('rag_evidence', {}),
                    data.get('repository_snapshot', {}).get('languages', [])
                )
            calculate(data)
            transition(data,'VIVA_PENDING')
            memory.record(data,'orchestrator','VERIFY',{'status':data['current_status'],'cycles':data['investigation_cycles'],'llm_calls':data['llm_calls']})
        except Exception as exc:
            data['stop_reason']=exc.code if isinstance(exc,AppError) else 'TOOL_FAILURE'
            data['error']=exc.message if isinstance(exc,AppError) else 'Analysis tool failed; inspect configured tools and repository availability'
            transition(data,'FAILED')
            memory.record(data,'orchestrator','ERROR',{'message':data['error']},'failed')
            logger.exception('Session %s failed (%s)',sid,type(exc).__name__)

def execute_cycle(data,root,files,sha,plan,number):
    cycle={'cycle_number':number,'started_at':memory.now(),'finished_at':None,'plan':plan,'decision_summary':plan['rationale'],
        'selected_tools':[a['tool'] for a in plan['actions']],'executions':[],'observations':{},'replanning_decision':None,'stop_reason':None}
    data['agent_cycles'].append(cycle)
    memory.save(data)
    for action in plan['actions']:
        try:
            evidence,edges,observation=tool(data,action['tool'],code_agent.act,root,files,sha,action)
        except (ValueError,AppError) as exc:
            if isinstance(exc,AppError) and exc.code=='TIME_BUDGET_EXCEEDED':
                raise
            cycle['executions'].append({'tool':action['tool'],'inputs':action,'status':'failed','error':str(exc)})
            cycle['replanning_decision']='Invalid action rejected; request a corrected plan within remaining budget.'
            data['_invalid_actions']=data.get('_invalid_actions',0)+1
            data['missing_evidence'].append('Rejected tool selection; select only known inventory paths and symbols.')
            memory.save(data)
            if data['_invalid_actions']>=2:
                raise AppError('Repeated invalid tool selections',502,'INVALID_TOOL_SELECTION') from exc
            break
        merge(data,evidence,edges)
        cycle['executions'].append({'tool':action['tool'],'inputs':action,'status':'completed','outputs':observation,'evidence_ids':[e['evidence_id'] for e in evidence]})
        memory.record(data,'code','ACT_AGAIN',{'action':action,'result':observation},events=[('skill_evidence',evidence)])
    cycle['finished_at']=memory.now()
    cycle['observations']={'evidence_count':len(data['code_evidence']),'missing_evidence':data['missing_evidence']}
    memory.save(data)
