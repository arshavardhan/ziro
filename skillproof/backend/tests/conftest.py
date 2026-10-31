import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / '.deps'))

import pytest
from fastapi.testclient import TestClient
import config
from main import app
from agents import orchestrator,planner,repository_agent,skill_evaluator,viva_generator,viva_evaluator
from scripts.create_demo_repo import create
from services.repository_service import inspect_snapshot
from schemas.agents import Plan,Assessments
from schemas.viva import Questions
from tools.ast_tool import analyze

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'DB_PATH',tmp_path/'test.sqlite3')
    monkeypatch.setattr(config,'WORKSPACES',tmp_path/'workspaces')
    monkeypatch.setattr(config,'CREDENTIALS',tmp_path/'credentials')
    monkeypatch.setattr(config,'SIGNING_SECRET','synthetic-test-secret-'*3)
    monkeypatch.setattr(config,'REVIEWER_TOKEN','review-test')
    monkeypatch.setattr(orchestrator,'submit',orchestrator.run)
    with TestClient(app) as client:
        yield client

@pytest.fixture
def workflow(client,tmp_path,monkeypatch):
    root=create(tmp_path/'repo')
    repo=inspect_snapshot(root,'https://github.com/demo/skillproof')
    all_evidence=analyze(repo[1],repo[2]['commit_sha'])
    source=next(e for e in all_evidence if e['symbol']=='total')
    calls=[]
    def reason(task,evidence,schema):
        calls.append(task)
        if schema is Plan:
            initial=task.startswith('PLAN:')
            return Plan(rationale='Inspect totals; then find matching tests',actions=[dict(tool='inspect_files' if initial else 'find_tests',files=['orders.py'],reason='Validate implementation/test links')],missing_evidence=[] if initial else ['Runtime execution unavailable']).model_dump(mode='json')
        if schema is Assessments:
            return {'assessments':[dict(skill=s,implementation_score=90,architecture_score=80,confidence=.9,
                supporting_evidence=[source['evidence_id']],missing_evidence=['Candidate authorship unknown'],limitations=[],
                observed_facts=['total validates negative prices'],ai_inferences=['Supports Python skills'],verdict='PARTIALLY_VERIFIED') for s in evidence['skills']]}
        if schema is Questions:
            return {'questions':[dict(question_id=f'q{i}',question=f'Explain total validation part {i}',category=kind,difficulty='medium',
                related_file='orders.py',related_function='total',expected_concepts=['validation','rounding'],evidence_reference=source['evidence_id'],
                evaluation_rubric={'correctness':'Must explain negative input handling'},parent_question_id=None) for i,kind in enumerate(['conceptual','conceptual','implementation','implementation','debugging'],1)]}
        score=15 if evidence['answer']=='wrong' else 90
        return dict(technical_correctness=score,code_understanding=score,reasoning=score,evidence_alignment=score,limitations_awareness=score,
            evidence_reference=evidence['question']['evidence_reference'],feedback='Synthetic rubric result',incomplete=evidence['answer']=='incomplete',
            follow_up_question='How would you validate negative quantities?' if evidence['answer']=='incomplete' else None)
    for module in [planner,skill_evaluator,viva_generator,viva_evaluator]:
        monkeypatch.setattr(module,'reason',reason)
    monkeypatch.setattr(repository_agent,'run',lambda *args:repo)
    import tools.pytest_tool as pytest_tool
    monkeypatch.setattr(pytest_tool.shutil,'which',lambda name:None)
    response=client.post('/api/analyze',json={'github_url':'https://github.com/demo/skillproof','candidate_id':'CAND-001','claimed_skills':['Python']})
    assert response.status_code==202,response.text
    sid=response.json()['session_id']
    state=client.get('/api/session/'+sid).json()
    assert state['current_status']=='VIVA_PENDING',state
    return sid,calls

@pytest.fixture
def completed(client,workflow):
    sid,calls=workflow
    for i in range(1,6):
        response=client.post(f'/api/viva/{sid}/answer',json={'question_id':f'q{i}','answer':'Correct repository-specific explanation'})
        assert response.status_code==200,response.text
    return sid,calls
