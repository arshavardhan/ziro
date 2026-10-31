import hmac
from fastapi import Header
import config
from core.exceptions import AppError

def reviewer(x_reviewer_token: str = Header(default='')):
    if not config.REVIEWER_TOKEN:
        raise AppError('Configure REVIEWER_TOKEN before human review',503,'NOT_CONFIGURED')
    if not hmac.compare_digest(x_reviewer_token,config.REVIEWER_TOKEN):
        raise AppError('Valid reviewer token required',403,'FORBIDDEN')
