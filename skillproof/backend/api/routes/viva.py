from fastapi import APIRouter
from schemas.viva import QuestionsResponse,AnswerRequest,AnswerResponse
from database import repositories as memory
from services.session_service import answer

router=APIRouter(tags=['viva'])

@router.get('/viva/{session_id}/questions',response_model=QuestionsResponse)
def questions(session_id:str):
    data=memory.get(session_id)
    return dict(session_id=session_id,questions=data['viva_questions'],answered_ids=list(data['viva_responses']))

@router.post('/viva/{session_id}/answer',response_model=AnswerResponse)
def submit_answer(session_id:str,request:AnswerRequest):
    return answer(session_id,request)
