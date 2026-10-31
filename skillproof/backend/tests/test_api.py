import pytest
from database import repositories as memory

HEADER={'X-Reviewer-Token':'review-test'}
APPROVE={'approved':True,'reviewer':'Human','reason':'Reviewed all evidence and execution limitations'}

def test_all_read_endpoints(client,workflow):
    sid,calls=workflow
    assert client.get('/health').json()['contract_version']=='2.0'
    for path in [f'/api/session/{sid}',f'/api/session/{sid}/timeline',f'/api/session/{sid}/evidence',f'/api/session/{sid}/report',f'/api/viva/{sid}/questions']:
        response=client.get(path)
        assert response.status_code==200,response.text
    assert len(calls)==5
    data=memory.get(sid)
    assert data['investigation_cycles']==3
    assert data['commit_summary']['commit_count']==3
    assert data['test_results']['execution']=='NOT_PERFORMED'
    assert {'PLAN','ACT','OBSERVE','CRITIQUE','RE-PLAN','ACT_AGAIN','VERIFY'} <= {s['phase'] for s in data['agent_steps']}

def test_full_approval_issuance(client,completed):
    sid,_=completed
    assert client.post(f'/api/credential/{sid}/issue',headers=HEADER).status_code==409
    assert client.post(f'/api/approve/{sid}',json=APPROVE).status_code==403
    assert client.post(f'/api/approve/{sid}',headers=HEADER,json=APPROVE).status_code==200
    result=client.post(f'/api/credential/{sid}/issue',headers=HEADER)
    assert result.status_code==200,result.text
    payload=result.json()
    cid=payload['credential_id']
    assert len(payload['repository_commit_sha'])==40
    assert client.get('/api/credential/'+cid).json()==payload
    assert client.get(f'/api/credential/{cid}/verify').json()['valid']
    assert client.post('/api/credential/verify',json=payload).json()['valid']
    assert client.post(f'/api/credential/{sid}/issue',headers=HEADER).json()['credential_id']==cid
    payload['candidate_id']='TAMPERED'
    assert not client.post('/api/credential/verify',json=payload).json()['valid']

def test_rejection_is_terminal(client,completed):
    sid,_=completed
    response=client.post(f'/api/approve/{sid}',headers=HEADER,json={**APPROVE,'approved':False})
    assert response.json()['current_status']=='REJECTED'
    assert client.post(f'/api/credential/{sid}/issue',headers=HEADER).status_code==409
    assert client.post(f'/api/approve/{sid}',headers=HEADER,json=APPROVE).status_code==409

def test_followup_required(client,workflow):
    sid,_=workflow
    r=client.post(f'/api/viva/{sid}/answer',json={'question_id':'q1','answer':'incomplete'})
    assert r.json()['follow_up']['question_id']=='q1-followup'
    for i in range(2,6):
        client.post(f'/api/viva/{sid}/answer',json={'question_id':f'q{i}','answer':'correct'})
    assert client.get(f'/api/session/{sid}').json()['current_status']=='VIVA_PENDING'
    assert client.post(f'/api/approve/{sid}',headers=HEADER,json=APPROVE).status_code==409
    r=client.post(f'/api/viva/{sid}/answer',json={'question_id':'q1-followup','answer':'correct'})
    assert r.json()['current_status']=='APPROVAL_PENDING'

def test_incorrect_viva_blocks_review(client,workflow):
    sid,_=workflow
    for i in range(1,6):
        client.post(f'/api/viva/{sid}/answer',json={'question_id':f'q{i}','answer':'wrong'})
    assert client.post(f'/api/approve/{sid}',headers=HEADER,json=APPROVE).status_code==409

def test_question_errors(client,workflow):
    sid,_=workflow
    assert client.post(f'/api/viva/{sid}/answer',json={'question_id':'missing','answer':'answer'}).status_code==404
    request={'question_id':'q1','answer':'answer'}
    assert client.post(f'/api/viva/{sid}/answer',json=request).status_code==200
    assert client.post(f'/api/viva/{sid}/answer',json=request).status_code==409

@pytest.mark.parametrize('path',['/api/session/missing','/api/session/missing/report','/api/session/missing/evidence','/api/session/missing/timeline','/api/credential/missing'])
def test_not_found_error_schema(client,path):
    response=client.get(path)
    assert response.status_code==404
    assert response.json()['error']['code']=='NOT_FOUND'

def test_validation_error_schema(client):
    response=client.post('/api/analyze',json={'github_url':'file:///tmp','candidate_id':'C','claimed_skills':['Python']})
    assert response.status_code==422
    assert response.json()['error']['code']=='VALIDATION_ERROR'

def test_cors(client):
    response=client.options('/api/analyze',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST'})
    assert response.headers['access-control-allow-origin']=='http://localhost:5173'
