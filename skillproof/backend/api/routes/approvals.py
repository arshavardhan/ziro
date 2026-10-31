from fastapi import APIRouter,Depends
from security.secrets import reviewer
from schemas.session import ApprovalRequest,ApprovalResponse
from services.session_service import approve

router=APIRouter(tags=['approvals'])

@router.post('/approve/{session_id}',response_model=ApprovalResponse,dependencies=[Depends(reviewer)])
def approval(session_id:str,request:ApprovalRequest):
    return approve(session_id,request)
