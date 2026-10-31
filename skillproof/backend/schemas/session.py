from typing import Literal
from pydantic import Field
from schemas.candidate import StrictModel
from schemas.evidence import Evidence, GraphEdge, TestResult, SimilarityFinding, SkillScore, Assessment
from schemas.agents import TimelineEvent, Plan
from schemas.viva import Question, AnswerResponse
from core.enums import Status
from schemas.provenance import BaselineRecord,TestDiscovery,TestExecution,EvaluationDisclosure,AgentCycle

class AnalyzeResponse(StrictModel):
    session_id: str
    status: Literal['QUEUED'] = 'QUEUED'
    message: str = 'Analysis queued'

class ApprovalRequest(StrictModel):
    approved: bool
    reviewer: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=2000)

class ApprovalResponse(StrictModel):
    approval_status: Literal['approved','rejected']
    current_status: Status
    reviewer: str
    reason: str
    timestamp: str

class RepositorySnapshot(StrictModel):
    repository_url: str
    commit_sha: str
    captured_at: str
    languages: list[str]
    files: list[str]
    directory_tree: list[str]
    dependencies: list[str]
    entry_points: list[str]
    ci_workflows: list[str]
    context: dict[str,str]
    limitations: list[str]
    owner: str | None = None
    name: str | None = None
    default_branch: str | None = None
    cloned_at: str | None = None
    file_hashes: dict[str,str] = {}

class GitCommit(StrictModel):
    sha: str
    author_name: str
    author_email: str
    timestamp: str
    message: str
    changed_files: list[str]
    additions: int
    deletions: int
    test_modifications: list[str]
    documentation_modifications: list[str]

class GitSummary(StrictModel):
    commit_count: int = 0
    commits: list[GitCommit] = []
    file_introduction: dict[str,str] = {}
    anomalies: list[str] = []
    feature_progression: list[str] = []
    limitations: list[str] = []

class SessionResponse(StrictModel):
    session_id: str
    candidate_id: str
    github_url: str
    claimed_skills: list[str]
    current_status: Status
    repository_commit_sha: str | None = None
    repository_snapshot: RepositorySnapshot | None = None
    analysis_plan: Plan | None = None
    agent_steps: list[TimelineEvent] = []
    code_evidence: list[Evidence] = []
    evidence_graph: list[GraphEdge] = []
    commit_summary: GitSummary = Field(default_factory=GitSummary)
    test_results: TestResult = Field(default_factory=TestResult)
    similarity_findings: list[SimilarityFinding] = []
    assessments: list[Assessment] = []
    skill_scores: dict[str,SkillScore] = {}
    viva_questions: list[Question] = []
    viva_responses: dict[str,AnswerResponse] = {}
    approval_status: str = 'pending'
    approval: ApprovalResponse | None = None
    missing_evidence: list[str] = []
    limitations: list[str] = []
    error: str | None = None
    investigation_cycles: int = 0
    llm_calls: int = 0
    baseline: BaselineRecord | None = None
    test_discovery: TestDiscovery | None = None
    test_execution: TestExecution | None = None
    synthetic_evaluation: EvaluationDisclosure | None = None
    agent_cycles: list[AgentCycle] = []
    stop_reason: str | None = None
    rag_indexed: bool = False
    rag_chunks_count: int = 0
    rag_evidence: dict = {}
    resume_info: dict | None = None
    resume_verification: dict | None = None

class ReportResponse(StrictModel):
    session_id: str
    current_status: Status
    repository_commit_sha: str | None
    skill_report: list[SkillScore]
    evidence_references: list[Evidence]
    test_results: TestResult
    git_findings: GitSummary
    similarity_findings: list[SimilarityFinding]
    viva_evaluation: dict[str,AnswerResponse]
    missing_evidence: list[str]
    limitations: list[str]
    approval_status: str
    eligible_skills: list[str]
    blocking_reasons: list[str]
    baseline: BaselineRecord | None = None
    test_discovery: TestDiscovery | None = None
    test_execution: TestExecution | None = None
    synthetic_evaluation: EvaluationDisclosure | None = None
    sections: dict = {}
    stop_reason: str | None = None
    resume_info: dict | None = None
    resume_verification: dict | None = None

class ErrorDetail(StrictModel):
    code: str
    message: str
    details: list[dict] = []

class ErrorResponse(StrictModel):
    error: ErrorDetail

class HealthResponse(StrictModel):
    status: Literal['ok'] = 'ok'
    contract_version: str = '2.0'
    llm_configured: bool
    signing_configured: bool
