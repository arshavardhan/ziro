from fastapi import APIRouter
from api.routes import analysis,sessions,evidence,viva,approvals,credentials

router=APIRouter()
for module in (analysis,sessions,evidence,viva,approvals,credentials):
    router.include_router(module.router)
