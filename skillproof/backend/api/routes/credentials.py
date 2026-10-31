from fastapi import APIRouter,Depends
from security.secrets import reviewer
from schemas.credentials import Credential,VerificationResponse
from services import credential_service
from agents.credential_agent import run

router=APIRouter(tags=['credentials'])

@router.post('/credential/verify',response_model=VerificationResponse)
def verify(payload:dict):
    return credential_service.verify_payload(payload)

@router.post('/credential/{session_id}/issue',response_model=Credential,response_model_exclude_unset=True,dependencies=[Depends(reviewer)])
def issue(session_id:str):
    return run(session_id)

@router.get('/credential/{credential_id}',response_model=Credential,response_model_exclude_unset=True)
def get(credential_id:str):
    return credential_service.get(credential_id)

@router.get('/credential/{credential_id}/verify',response_model=VerificationResponse)
def verify_stored(credential_id:str):
    return credential_service.verify_payload(credential_service.get(credential_id))
