from fastapi import APIRouter
from schemas.session import SessionResponse,ReportResponse
from schemas.agents import TimelineResponse
from database import repositories as memory
from services.session_service import report

router=APIRouter(tags=['sessions'])

@router.get('/session/{session_id}',response_model=SessionResponse)
def session(session_id:str):
    return memory.public(memory.get(session_id))

@router.get('/session/{session_id}/timeline',response_model=TimelineResponse)
def timeline(session_id:str):
    return {'session_id':session_id,'events':memory.get(session_id)['agent_steps']}

@router.get('/session/{session_id}/report',response_model=ReportResponse)
def get_report(session_id:str):
    return report(session_id)
