from agents import orchestrator,planner,llm
from database import repositories as memory
from database.migrations import migrate
from core.exceptions import AppError
import config
import httpx
from schemas.agents import Plan

def test_restart_recovery(client,workflow,monkeypatch):
    sid,calls=workflow
    data=memory.get(sid)
    data['current_status']='EVALUATING'
    data['_checkpoint'].pop('questions')
    data['_checkpoint'].pop('analysis_complete')
    memory.save(data)
    migrate()
    assert sid in memory.pending()
    before=len(calls)
    orchestrator.recover()
    assert memory.get(sid)['current_status']=='VIVA_PENDING'
    assert len(calls)==before+1

def test_llm_failure_persisted(client,monkeypatch):
    monkeypatch.setattr(config,'LLM_API_KEY','')
    r=client.post('/api/analyze',json={'github_url':'https://github.com/a/b','candidate_id':'C','claimed_skills':['Python']})
    data=memory.get(r.json()['session_id'])
    assert data['current_status']=='FAILED'
    assert data['llm_calls']==0

def test_real_llm_adapter_multiple_requests(monkeypatch):
    """Synthetic transport exercise, not live model intelligence validation."""
    original=httpx.Client
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json={'choices':[{'message':{'content':Plan(rationale='Synthetic provider response').model_dump_json()}}]})
    monkeypatch.setattr(config,'LLM_API_KEY','synthetic-key')
    monkeypatch.setattr(llm.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(handler)))
    planner.plan({'skills':['Python']})
    planner.critique({'inventory':['a.py']})
    assert len(calls)==2
    assert all(request.url.path.endswith('/chat/completions') for request in calls)

def test_missing_evidence_cannot_be_approved(client,completed):
    from services.scoring_service import eligible
    sid,_=completed
    data=memory.get(sid)
    data['assessments'][0]['supporting_evidence']=[]
    assert not eligible(data)[0]

def test_llm_invalid_json_is_bounded(monkeypatch):
    import pytest
    original=httpx.Client
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(200,json={'choices':[{'message':{'content':'not json'}}]})
    monkeypatch.setattr(config,'LLM_API_KEY','synthetic-key')
    monkeypatch.setattr(llm.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(handler)))
    with pytest.raises(AppError):
        planner.plan({'skills':['Python']})
    assert len(requests)==2
