from pydantic import BaseModel, Field


class EvaluationCase(BaseModel):
    id: str
    input: str
    tenant_id: str = "tenant_eval"
    app_id: str = "eval"
    session_id: str


class EvaluationMetrics(BaseModel):
    identity_leakage_score: float
    rehydration_accuracy: float
    transformation_correctness: float
    quality_delta: float
    latency_overhead: float


class EvaluationCaseResult(BaseModel):
    id: str
    input: str
    transformed: str
    rehydrated: str
    leaked_values: list[str] = Field(default_factory=list)
    latency_seconds: float


class EvaluationReport(BaseModel):
    dataset: str
    case_count: int
    metrics: EvaluationMetrics
    cases: list[EvaluationCaseResult] = Field(default_factory=list)
