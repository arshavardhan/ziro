from typing import Literal
from pydantic import Field
from schemas.candidate import StrictModel
from schemas.evidence import Assessment

class ToolAction(StrictModel):
    tool: Literal['inspect_files','trace_calls','find_tests']
    files: list[str] = Field(default_factory=list, max_length=15)
    symbol: str | None = Field(default=None, max_length=150)
    reason: str = Field(max_length=1000)

class Plan(StrictModel):
    rationale: str = Field(max_length=1500,description='Concise decision summary, not private chain-of-thought')
    languages: list[str] = Field(default_factory=lambda:['Python'], max_length=10)
    actions: list[ToolAction] = Field(default_factory=list, max_length=8)
    missing_evidence: list[str] = Field(default_factory=list, max_length=15)
    stop: bool = False

class Assessments(StrictModel):
    assessments: list[Assessment]

class TimelineEvent(StrictModel):
    event_id: str
    sequence: int
    timestamp: str
    agent: str
    phase: str
    status: Literal['started','completed','failed','info']
    observation: dict

class TimelineResponse(StrictModel):
    session_id: str
    events: list[TimelineEvent]
