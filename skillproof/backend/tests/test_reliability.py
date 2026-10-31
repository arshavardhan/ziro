"""Additive reliability regressions; separate from the unchanged 22 synthetic evaluation cases."""
import copy
import hashlib
import json
from pathlib import Path
import httpx
import pytest
import config
from agents import orchestrator,repository_agent,llm,planner,viva_generator
from core.exceptions import AppError
from database import repositories as memory
from database.connection import connect
from database.migrations import migrate
from services.provenance_service import freeze_baseline,get_baseline
from services.scoring_service import calculate,eligible
from services.evaluation_service import disclosure
from tools import pytest_tool

def test_discovery_execution_separate(client,workflow):
    sid,_=workflow
    data=client.get(f'/api/session/{sid}').json()
    assert data['test_discovery']['definitions_discovered']==3
    assert data['test_execution']['status']=='NOT_PERFORMED'
    assert data['test_execution']['tests_executed']==0
    assert data['test_execution']['tests_passed']==0
    assert data['test_results']['passed'] is None

def test_docker_unavailable_never_spawns_candidate(monkeypatch,tmp_path):
    monkeypatch.setattr(pytest_tool.shutil,'which',lambda _:None)
    monkeypatch.setattr(pytest_tool.subprocess,'Popen',lambda *a,**kw:pytest.fail('Host execution forbidden'))
    result=pytest_tool.run(tmp_path,{'test_a.py':'def test_a():\n assert True'},[])
    assert result['capability_check']['available'] is False
    assert result['execution_record']['reason']=='Docker unavailable'

def test_docker_present_but_unusable_is_blocked(monkeypatch,tmp_path):
    monkeypatch.setattr(pytest_tool.shutil,'which',lambda _:'docker')
    monkeypatch.setattr(pytest_tool.subprocess,'run',lambda *a,**kw:type('Result',(),{'returncode':1})())
    result=pytest_tool.run(tmp_path,{'test_a.py':'def test_a():\n assert True'},[])
    assert result['execution_record']['status']=='BLOCKED'
    assert result['execution_record']['tests_executed']==0

def test_baseline_serialization_and_sha(client,workflow):
    sid,_=workflow
    data=memory.get(sid); baseline=get_baseline(sid)
    assert baseline['repository']['commit_sha']==data['repository_commit_sha']
    assert baseline['analysis']['source_findings']==len(data['code_evidence'])
    assert baseline['analysis']['test_definitions_discovered']==3
    assert baseline['provenance']['analyzer_version']==config.ANALYZER_VERSION
    assert baseline['repository']['clone_timestamp'] is None  # Local test fixture has no recorded clone timestamp.

def test_frozen_baseline_does_not_change(client,workflow):
    sid,_=workflow
    original=get_baseline(sid)
    changed=memory.get(sid);changed['code_evidence']=[]
    assert freeze_baseline(changed)==original

def test_repeated_and_new_commit_classification(client,workflow):
    sid,_=workflow
    old=memory.get(sid)
    repeated=copy.deepcopy(old);repeated['session_id']='repeat'
    assert freeze_baseline(repeated)['record_kind']=='REPEATED_SAME_COMMIT'
    new=copy.deepcopy(old);new['session_id']='new';new['repository_commit_sha']='b'*40
    assert freeze_baseline(new)['record_kind']=='NEW_COMMIT'
    assert get_baseline(sid)['repository']['commit_sha']==old['repository_commit_sha']

def test_original_files_preserved():
    root=config.ROOT.parent/'artifacts'
    manifest=json.loads((root/'history/original-v2/manifest.json').read_text())
    for name in ['aegis-static-report.json','aegis-summary.json','evaluation-results.json']:
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==manifest[name]
    data=json.loads((root/'aegis-static-report.json').read_text())
    assert (len(data['repository_snapshot']['files']),len(data['code_evidence']),data['commit_summary']['commit_count'],data['test_results']['discovered_tests'])==(52,383,33,121)

def test_synthetic_disclosure_not_skill_confidence(client):
    data=disclosure()
    assert (data['total_cases'],data['passed'],data['classification_metric_fixture_count'])==(22,22,6)
    assert data['real_world_accuracy_claim'] is False
    assert 'not as estimates of real-world accuracy' in data['limitations']

def test_evidence_context_and_traceability(client,completed):
    sid,_=completed
    data=client.get(f'/api/session/{sid}').json()
    ids={e['evidence_id'] for e in data['code_evidence']}
    assert all(e['assessment_id']==sid and e['candidate_id']==data['candidate_id'] for e in data['code_evidence'])
    score=data['skill_scores']['Python']
    assert score['traceability']['valid']
    assert set(score['supporting_evidence'])<=ids

def test_duplicate_evidence_no_score_inflation(client,completed):
    sid,_=completed;data=memory.get(sid)
    first=calculate(data)['Python']['score']
    data['assessments'][0]['supporting_evidence']*=10
    data['code_evidence']*=3
    second=calculate(data)['Python']
    assert second['score']==first
    assert len(second['supporting_evidence'])==1

def test_missing_citation_invalidates_score(client,completed):
    sid,_=completed;data=memory.get(sid)
    data['assessments'][0]['supporting_evidence'].append('invented')
    assert calculate(data)['Python']['score'] is None
    assert not eligible(data)[0]

def test_unavailable_tests_not_failure(client,completed):
    sid,_=completed;data=memory.get(sid)
    score=calculate(data)['Python']
    assert score['test_score'] is None
    assert score['score']>65
    assert score['evidence_coverage']==80

def test_viva_source_ranges(client,workflow):
    sid,_=workflow;data=memory.get(sid)
    by_id={e['evidence_id']:e for e in data['code_evidence']}
    for q in data['viva_questions']:
        e=by_id[q['evidence_reference']]
        assert q['line_start']==e['line_start'] and q['line_end']==e['line_end']
        assert q['related_file']==e['file'] and q['related_function']==e['symbol']

def test_bad_viva_citation_rejected(client,workflow,monkeypatch):
    sid,_=workflow;data=memory.get(sid)
    questions=copy.deepcopy(data['viva_questions']);questions[0]['related_file']='imaginary.py'
    monkeypatch.setattr(viva_generator,'reason',lambda *a:{'questions':questions})
    with pytest.raises(AppError):
        viva_generator.run(data['code_evidence'])

def test_human_approval_and_signed_execution_limit(client,completed):
    sid,_=completed;headers={'X-Reviewer-Token':'review-test'}
    assert client.post(f'/api/credential/{sid}/issue',headers=headers).status_code==409
    assert client.post(f'/api/approve/{sid}',headers=headers,json={'approved':True,'reviewer':'Human','reason':'Reviewed limitation'}).status_code==200
    payload=client.post(f'/api/credential/{sid}/issue',headers=headers).json()
    assert payload['test_execution']['status']=='NOT_PERFORMED'
    assert client.post('/api/credential/verify',json=payload).json()['valid']
    payload['test_execution']['status']='PASSED'
    assert not client.post('/api/credential/verify',json=payload).json()['valid']

def test_llm_timeout_is_bounded(monkeypatch):
    original=httpx.Client;calls=[]
    def timeout(request):
        calls.append(request)
        raise httpx.ReadTimeout('timeout')
    monkeypatch.setattr(config,'LLM_API_KEY','test')
    monkeypatch.setattr(llm.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(timeout)))
    with pytest.raises(AppError,match='timed out'):
        planner.plan({})
    assert len(calls)==2

def test_cycles_include_real_outputs_and_limit(client,workflow):
    sid,_=workflow;data=memory.get(sid)
    assert len(data['agent_cycles'])==3
    assert data['stop_reason']=='INVESTIGATION_BUDGET_EXHAUSTED'
    assert all(c['executions'][0]['status']=='completed' and c['executions'][0]['outputs'] for c in data['agent_cycles'])

def test_repository_failure_recorded(client,monkeypatch):
    def fail(*args):
        raise AppError('Public repository unavailable',422,'REPOSITORY_UNAVAILABLE')
    monkeypatch.setattr(repository_agent,'run',fail)
    r=client.post('/api/analyze',json={'github_url':'https://github.com/missing/repository'})
    data=memory.get(r.json()['session_id'])
    assert data['stop_reason']=='REPOSITORY_UNAVAILABLE'
    assert data['llm_calls']==0

def test_model_missing_preserves_collected_repository(client,workflow,monkeypatch):
    sid,_=workflow
    monkeypatch.setattr(planner,'plan',lambda *args:(_ for _ in ()).throw(AppError('Configure Gemini',503,'LLM_NOT_CONFIGURED')))
    r=client.post('/api/analyze',json={'github_url':'https://github.com/demo/skillproof'})
    data=memory.get(r.json()['session_id'])
    assert data['current_status']=='FAILED' and data['baseline']
    assert data['code_evidence'] and data['repository_commit_sha']
    assert data['test_results']['execution']=='NOT_PERFORMED'

def test_resume_preserves_baseline(client,workflow):
    sid,_=workflow;original=get_baseline(sid);data=memory.get(sid)
    data['current_status']='EVALUATING';data['_checkpoint'].pop('questions');data['_checkpoint'].pop('analysis_complete')
    memory.save(data);migrate();orchestrator.recover()
    assert memory.get(sid)['current_status']=='VIVA_PENDING'
    assert get_baseline(sid)==original

def test_nine_report_sections(client,workflow):
    sid,_=workflow
    report=client.get(f'/api/session/{sid}/report').json()
    assert len(report['sections'])==9
    assert report['sections']['G_evaluation_limitations']['real_world_accuracy_claim'] is False
