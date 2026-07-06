from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "1.0"

TransactionEventType = Literal["transform", "rehydrate"]
PolicySource = Literal["enterprise", "cache", "fallback", "local", "package", "unknown"]


class TransactionPrivacy(BaseModel):
    raw_text_capture_enabled: bool = False
    raw_text_retention_days: int | None = Field(default=None, ge=0)
    raw_text_reference: str | None = None


class ReviewScores(BaseModel):
    detection_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    policy_coverage: float = Field(default=1.0, ge=0.0, le=1.0)
    leakage_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    rehydration_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    unresolved_token_count: int = Field(default=0, ge=0)
    explanations: list[str] = Field(default_factory=list)


class DetectionSummary(BaseModel):
    entity_type: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    text_preview: str | None = None


class MappingSummary(BaseModel):
    token: str
    entity_type: str


class PolicyDecisionSummary(BaseModel):
    entity_type: str
    action: str
    policy_id: str
    policy_version: str
    policy_source: PolicySource = "unknown"
    rule_id: str | None = None
    reason: str
    token: str | None = None
    token_strategy: str | None = None
    app_id: str | None = None
    role: str | None = None
    purpose: str | None = None
    direction: str | None = None
    environment: str | None = None
    matched_constraints: dict[str, str] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class RehydrationDecisionSummary(BaseModel):
    token: str
    entity_type: str | None = None
    allowed: bool
    reason: str
    status: str
    policy_id: str | None = None
    policy_version: str | None = None
    policy_source: PolicySource = "unknown"
    rule_id: str | None = None
    requester_roles: list[str] = Field(default_factory=list)
    required_roles: list[str] = Field(default_factory=list)
    purpose: str | None = None
    direction: str | None = None
    environment: str | None = None
    token_age_seconds: float | None = None
    max_token_age_seconds: int | None = None
    matched_constraints: dict[str, str] = Field(default_factory=dict)


class BaseTransactionEvent(BaseModel):
    schema_version: str = SCHEMA_VERSION
    event_id: str = Field(default_factory=lambda: f"txn_{uuid4().hex}")
    event_type: TransactionEventType
    tenant_id: str
    app_id: str
    session_id: str
    request_id: str
    environment: str | None = None
    policy_id: str | None = None
    policy_version: str | None = None
    policy_source: PolicySource = "unknown"
    input_fingerprint: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    scores: ReviewScores = Field(default_factory=ReviewScores)
    warnings: list[str] = Field(default_factory=list)
    privacy: TransactionPrivacy = Field(default_factory=TransactionPrivacy)
    raw_input_text: str | None = None

    @model_validator(mode="after")
    def _raw_capture_must_be_enabled(self) -> "BaseTransactionEvent":
        if self.raw_input_text is not None and not self.privacy.raw_text_capture_enabled:
            raise ValueError("raw_input_text requires raw_text_capture_enabled")
        return self


class TransformTransactionEvent(BaseTransactionEvent):
    event_type: Literal["transform"] = "transform"
    transformed_preview: str
    detections: list[DetectionSummary] = Field(default_factory=list)
    mappings: list[MappingSummary] = Field(default_factory=list)
    decisions: list[PolicyDecisionSummary] = Field(default_factory=list)


class RehydrationTransactionEvent(BaseTransactionEvent):
    event_type: Literal["rehydrate"] = "rehydrate"
    requested_text_preview: str
    rehydrated_preview: str
    requester_roles: list[str] = Field(default_factory=list)
    purpose: str | None = None
    decisions: list[RehydrationDecisionSummary] = Field(default_factory=list)


def fingerprint_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()
