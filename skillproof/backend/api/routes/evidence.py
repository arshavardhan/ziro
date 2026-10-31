from fastapi import APIRouter
from schemas.evidence import EvidenceResponse
from database import repositories as memory

router=APIRouter(tags=['evidence'])

@router.get('/session/{session_id}/evidence',response_model=EvidenceResponse)
def evidence(session_id:str):
    data=memory.get(session_id)
    from services.provenance_service import enrich_evidence
    data=enrich_evidence(data)
    return dict(session_id=session_id,repository_commit_sha=data['repository_commit_sha'],evidence=data['code_evidence'],relationships=data['evidence_graph'])
