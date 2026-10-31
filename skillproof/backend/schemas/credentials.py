from typing import Literal
from schemas.candidate import StrictModel
from schemas.evidence import SkillScore

class Credential(StrictModel):
    credential_id: str
    candidate_id: str
    repository_url: str
    repository_commit_sha: str
    verified_skills: list[str]
    skill_scores: dict[str,SkillScore]
    evidence_references: dict[str,list[str]]
    viva_summary: dict[str,float]
    issued_timestamp: str
    issuer: Literal['SkillProof AI'] = 'SkillProof AI'
    signature_algorithm: Literal['HMAC-SHA256'] = 'HMAC-SHA256'
    signature: str
    assessment_date: str | None = None
    evidence_summary: dict = {}
    test_execution: dict = {}
    assessment_limitations: list[str] = []

class VerificationResponse(StrictModel):
    valid: bool
    credential_id: str | None = None
