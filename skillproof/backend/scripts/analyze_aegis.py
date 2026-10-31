"""Collect real static evidence without executing AegisAI or inventing LLM results."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'.deps')]
import config
from database.migrations import migrate
from database import repositories as memory
from services.repository_service import inspect_snapshot
from services.evidence_service import build
from tools.git_tool import history
from tools.similarity_tool import indicators
from tools.pytest_tool import run
from schemas.viva import Question

URL='https://github.com/arshavardhan/AegisAi'
SHA='79112160653cc38cdcbddaf578e29ecfbd58a70a'
SKILLS=['Python','Object-Oriented Programming','Machine Learning','Software Architecture','Testing','Git/GitHub','API and Package Development']

def main():
    root,files,snapshot=inspect_snapshot(config.WORKSPACES/'aegis-fixed',URL)
    if snapshot['commit_sha']!=SHA:
        raise ValueError('Unexpected AegisAI commit; do not silently change the report baseline')
    evidence,graph=build(files,SHA)
    tests=run(root,files,graph)
    git=history(root,SHA)
    similarity=indicators(files)
    migrate()
    data=memory.create(dict(github_url=URL,candidate_id='CAND-001',claimed_skills=SKILLS,commit_sha=SHA))
    data.update(repository_snapshot=snapshot,repository_commit_sha=SHA,code_evidence=evidence,evidence_graph=graph,
        commit_summary=git,test_results=tests,similarity_findings=similarity,current_status='FAILED',
        error='Static analysis complete. Live LLM analysis and candidate viva have not been performed; submit a live session after configuring LLM_API_KEY.',
        limitations=['Static baseline only; no live LLM calls, candidate answers, approval or credential.', 'Repository was not modified or executed on the host.'],
        missing_evidence=['Live LLM plan, critique and skill assessment','Candidate viva answers','Explicit human review'],_workspace=str(root))
    memory.record(data,'deterministic_baseline','OBSERVE',{'commit_sha':SHA,'evidence_count':len(evidence),'llm_calls':0},events=[
        ('repository_snapshots',snapshot),('repository_files',list(files)),('skill_evidence',evidence),('test_results',tests),('git_findings',git),('similarity_findings',similarity)])
    # Human-authored, source-grounded draft questions, explicitly separate from live agent output.
    specs=[
        ('conceptual','aegis/uncertainty/entropy.py','EntropyEstimator.compute','Why divide Shannon entropy by log2(number of classes), and how does this implementation handle zero probabilities?',['normalization','zero probability limit','validation']),
        ('conceptual','aegis/scoring/aggregator.py','ScoreAggregator.aggregate','Why does the aggregator use 1 minus uncertainty and OOD risk? Explain the meaning and limits of this score.',['risk direction','weighted sum','uncalibrated heuristic']),
        ('implementation','aegis/core/pipeline.py','PredictionPipeline.predict_batch','Trace the entropy array from computation through the per-sample uncertainty variable into trust.compute. What checks protect array alignment?',['metric shapes','sample indexing','entropy argument']),
        ('implementation','aegis/scoring/trust.py','TrustScorer.compute','How does is_ood affect normalized_ood, and what happens when drift_score is None?',['hard OOD signal','optional drift','ScoreInputs']),
        ('debugging','aegis/core/pipeline.py','PredictionPipeline._validate_probabilities','A wrapper returns an N-by-1 matrix of ones. Why does validation reject it, and how would you design a compatible wrapper?',['two-class minimum','probability semantics','shape validation'])]
    questions=[]
    for i,(category,file,symbol,text,concepts) in enumerate(specs,1):
        item=next(e for e in evidence if e['file']==file and e['symbol']==symbol)
        questions.append(Question(question_id=f'q{i}',question=text,category=category,difficulty='medium',related_file=file,
            related_function=symbol,expected_concepts=concepts,evidence_reference=item['evidence_id'],
            evaluation_rubric={'technical_correctness':'30%: accurate source behavior','code_understanding':'25%: trace actual statements',
                'reasoning':'20%: justify approach','evidence_alignment':'15%: cite source','limitations_awareness':'10%: identify limits'}).model_dump(mode='json'))
    output=ROOT.parent/'artifacts'
    output.mkdir(exist_ok=True)
    (output/'aegis-static-report.json').write_text(json.dumps(memory.public(data).model_dump(mode='json'),indent=2),encoding='utf-8')
    (output/'aegis-draft-viva.json').write_text(json.dumps({'provenance':'Human-authored draft grounded in inspected source; not live LLM output','commit_sha':SHA,'questions':questions},indent=2),encoding='utf-8')
    (output/'aegis-request.json').write_text(json.dumps(dict(github_url=URL,candidate_id='CAND-001',claimed_skills=SKILLS,commit_sha=SHA),indent=2),encoding='utf-8')
    mapping={e['evidence_id']:e for e in evidence}
    trace=[dict(edge,source_symbol=mapping.get(edge['source'],{}).get('symbol',edge['source']),target_symbol=mapping.get(edge['target'],{}).get('symbol',edge['target'])) for edge in graph if edge['relation'].startswith('PASSES_VALUE:entropy')]
    summary={'session_id':data['session_id'],'commit_sha':SHA,'files':len(files),'evidence_items':len(evidence),'commits':git['commit_count'],
             'discovered_tests':tests['discovered_tests'],'test_execution':tests['execution'],'similarity_findings':len(similarity),'entropy_value_trace':trace}
    (output/'aegis-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    main()
