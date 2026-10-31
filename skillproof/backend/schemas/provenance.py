from typing import Literal
from schemas.candidate import StrictModel

class TestDiscovery(StrictModel):
    status: str = 'NOT_ATTEMPTED'
    definitions_discovered: int = 0
    discovery_method: str = 'STATIC_ANALYSIS'
    limitations: list[str] = ['Definitions are not executed tests or a coverage measure.']

class TestExecution(StrictModel):
    status: Literal['NOT_ATTEMPTED','NOT_PERFORMED','BLOCKED','RUNNING','PASSED','FAILED','PARTIALLY_PASSED','TIMED_OUT','ERROR'] = 'NOT_ATTEMPTED'
    tests_executed: int | None = 0
    tests_passed: int | None = 0
    tests_failed: int | None = 0
    tests_skipped: int | None = 0
    reason: str | None = None
    execution_id: str | None = None
    capability_check: dict | None = None
    counts_source: str = 'NO_EXECUTION_RECORD'

class BaselineRecord(StrictModel):
    assessment_id: str
    candidate_id: str
    record_kind: str
    prior_assessment_id: str | None = None
    repository: dict
    analysis: dict
    provenance: dict

class EvaluationDisclosure(StrictModel):
    evaluation_id: str | None = None
    evaluation_type: str = 'SYNTHETIC_REGRESSION'
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    result: str = 'UNAVAILABLE'
    classification_metric_fixture_count: int = 0
    classification_metrics: dict = {}
    real_world_accuracy_claim: bool = False
    evaluation_timestamp: str | None = None
    limitations: str

class AgentCycle(StrictModel):
    cycle_number: int
    started_at: str
    finished_at: str | None = None
    plan: dict
    decision_summary: str
    selected_tools: list[str]
    executions: list[dict] = []
    observations: dict = {}
    replanning_decision: str | None = None
    stop_reason: str | None = None
