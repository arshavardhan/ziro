from typing import Literal
from pydantic import Field
from schemas.candidate import StrictModel

class Question(StrictModel):
    question_id: str
    question: str
    category: Literal['conceptual','implementation','debugging']
    difficulty: Literal['easy','medium','hard']
    related_file: str
    related_function: str
    expected_concepts: list[str]
    evidence_reference: str
    evaluation_rubric: dict[str, str]
    parent_question_id: str | None = None
    skill: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    related_evidence_ids: list[str] = []

class Questions(StrictModel):
    questions: list[Question] = Field(min_length=5, max_length=5)

class QuestionsResponse(StrictModel):
    session_id: str
    questions: list[Question]
    answered_ids: list[str]

class AnswerRequest(StrictModel):
    question_id: str
    answer: str = Field(min_length=1, max_length=8000)

class VivaEvaluation(StrictModel):
    technical_correctness: float = Field(ge=0, le=100)
    code_understanding: float = Field(ge=0, le=100)
    reasoning: float = Field(ge=0, le=100)
    evidence_alignment: float = Field(ge=0, le=100)
    limitations_awareness: float = Field(ge=0, le=100)
    evidence_reference: str
    feedback: str
    incomplete: bool
    follow_up_question: str | None = None

class AnswerResponse(StrictModel):
    question_id: str
    answer: str
    evaluation: VivaEvaluation
    weighted_score: float
    follow_up: Question | None = None
    current_status: str
