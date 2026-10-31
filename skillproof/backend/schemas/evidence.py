from typing import Literal
from pydantic import Field
from schemas.candidate import StrictModel
from core.enums import EvidenceState

class Evidence(StrictModel):
    evidence_id: str
    commit_sha: str
    file: str
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    symbol: str
    kind: Literal['function','method','class','documentation','module']
    state: EvidenceState
    signature: str = ''
    type_hints: list[str] = []
    docstring: str | None = None
    calls: list[str] = []
    imports: list[str] = []
    exceptions: list[str] = []
    complexity: int | None = None
    source: str
    observed_facts: list[str] = []
    limitations: list[str] = []
    test_references: list[str] = []
    assessment_id: str | None = None
    candidate_id: str | None = None
    claimed_skills: list[str] = []
    evidence_type: Literal['CODE_IMPLEMENTATION','ARCHITECTURE','STATIC_ANALYSIS','TEST_DISCOVERY','TEST_EXECUTION','GIT_HISTORY','DOCUMENTATION','VIVA_RESPONSE'] = 'STATIC_ANALYSIS'
    collection_tool: str | None = None
    collected_at: str | None = None
    raw_observation: dict = {}
    interpretation: str | None = None
    evidence_strength: str = 'UNASSESSED'
    verification_status: str = 'UNVERIFIED'

class GraphEdge(StrictModel):
    source: str
    target: str
    relation: str
    file: str
    line: int | None = None
    resolution: str = 'static'

class SimilarityFinding(StrictModel):
    finding_id: str
    files: list[str]
    lines: list[int]
    similarity: float = Field(ge=0, le=1)
    measure: str
    evidence: str
    severity: Literal['low','medium','high']
    explanation: str
    limitations: list[str]

class TestResult(StrictModel):
    execution: Literal['NOT_PERFORMED','PERFORMED'] = 'NOT_PERFORMED'
    status: Literal['NOT_PERFORMED','PASSED','FAILED','ERROR','TIMEOUT'] = 'NOT_PERFORMED'
    framework: str = 'pytest'
    discovered_tests: int = 0
    collected_tests: int | None = None
    passed: int | None = None
    failed: int | None = None
    skipped: int | None = None
    collection_errors: int | None = None
    runtime_seconds: float | None = None
    exit_code: int | None = None
    output: str = ''
    reason: str | None = None
    test_to_module: list[GraphEdge] = []
    limitations: list[str] = []
    execution_record: dict | None = None
    capability_check: dict | None = None

class Assessment(StrictModel):
    skill: str
    implementation_score: float | None = Field(default=None, ge=0, le=100)
    architecture_score: float | None = Field(default=None, ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    supporting_evidence: list[str]
    missing_evidence: list[str]
    limitations: list[str]
    observed_facts: list[str]
    ai_inferences: list[str]
    verdict: Literal['PARTIALLY_VERIFIED','INSUFFICIENT_EVIDENCE','NOT_DEMONSTRATED','VERIFIED']

class SkillScore(StrictModel):
    skill: str
    score: float | None
    implementation_score: float | None
    test_score: float | None
    architecture_score: float | None
    git_score: float | None
    viva_score: float | None
    evidence_coverage: float
    verdict: str
    supporting_evidence: list[str]
    missing_evidence: list[str]
    limitations: list[str]
    status: str = 'UNVERIFIED'
    evidence_dimensions: dict = {}
    traceability: dict = {}
    scoring_weights: dict[str,float] = {}

class EvidenceResponse(StrictModel):
    session_id: str
    repository_commit_sha: str | None
    evidence: list[Evidence]
    relationships: list[GraphEdge]
