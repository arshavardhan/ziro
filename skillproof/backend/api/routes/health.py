from fastapi import APIRouter
import config
from schemas.session import HealthResponse

router=APIRouter(tags=['health'])

@router.get('/health',response_model=HealthResponse)
def health():
    return HealthResponse(llm_configured=bool(config.LLM_API_KEY),signing_configured=len(config.SIGNING_SECRET)>=32)
