from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from core.guardrails import validate_url
import uuid

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class AnalyzeRequest(StrictModel):
    github_url: str | None = None
    repo_url: str | None = None
    candidate_id: str = Field(default_factory=lambda:'CAND-'+uuid.uuid4().hex[:12], min_length=1, max_length=100, pattern=r'^[\w-]+$')
    claimed_skills: list[str] = Field(default_factory=lambda:['Repository implementation'], min_length=1, max_length=20)
    commit_sha: str | None = Field(default=None, pattern=r'^[0-9a-fA-F]{40}$')
    description: str | None = None
    resume_text: str | None = None
    resume_filename: str | None = None
    resume_skills: list[str] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def populate_url(cls, data):
        if isinstance(data, dict):
            if not data.get('github_url') and data.get('repo_url'):
                data['github_url'] = data['repo_url']
            elif not data.get('github_url'):
                raise ValueError('Field github_url is required')
        return data

    @field_validator('github_url')
    @classmethod
    def url(cls, value):
        return validate_url(value)

    @field_validator('claimed_skills')
    @classmethod
    def skills(cls, values):
        if any(not v.strip() or len(v) > 80 for v in values):
            raise ValueError('Skills must contain 1–80 characters')
        return list(dict.fromkeys(v.strip() for v in values))
