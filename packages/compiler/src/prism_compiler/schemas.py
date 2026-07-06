from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class PolicyCacheInvalidateRequest(BaseModel):
    tenant_id: str | None = None
    app_id: str | None = None


class PolicyCacheInvalidateResponse(BaseModel):
    removed: int


class RuntimePolicyStatusResponse(BaseModel):
    tenant_id: str
    app_id: str
    policy_id: str
    policy_version: str
    policy_source: Literal["enterprise", "cache", "fallback", "local"]
    policy_cache_hit: bool
    policy_cache_stale: bool
    policy_provider_latency_ms: float
    diagnostics: list[str] = Field(default_factory=list)


class EntityDetection(BaseModel):
    text: str
    entity_type: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    metadata: dict[str, str] = Field(default_factory=dict)


class TokenMapping(BaseModel):
    token: str
    entity_type: str
    metadata: dict[str, str] = Field(default_factory=dict)


class TransformationDecision(BaseModel):
    entity_type: str
    action: str
    policy_id: str
    policy_version: str
    policy_source: Literal["enterprise", "cache", "fallback", "local", "package", "unknown"] = (
        "unknown"
    )
    policy_cache_hit: bool | None = None
    policy_cache_stale: bool | None = None
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
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class AuditEvent(BaseModel):
    event_type: str
    tenant_id: str
    app_id: str
    session_id: str
    request_id: str
    policy_id: str | None = None
    policy_version: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str] = Field(default_factory=dict)


class TransformRequest(BaseModel):
    tenant_id: str
    app_id: str
    session_id: str
    text: str
    policy_id: str | None = None
    purpose: str | None = None
    direction: str | None = None
    environment: str | None = None
    policy_source: (
        Literal["enterprise", "cache", "fallback", "local", "package", "unknown"] | None
    ) = None
    policy_cache_hit: bool | None = None
    policy_cache_stale: bool | None = None
    policy_provider_latency_ms: float | None = None


class TransformResponse(BaseModel):
    request_id: str
    transformed_text: str
    detections: list[EntityDetection] = Field(default_factory=list)
    mappings: list[TokenMapping] = Field(default_factory=list)
    decisions: list[TransformationDecision] = Field(default_factory=list)
    audit_event: AuditEvent


class RehydrateRequest(BaseModel):
    tenant_id: str
    app_id: str
    session_id: str
    text: str
    roles: list[str] = Field(default_factory=list)
    purpose: str | None = None
    direction: str | None = None
    environment: str | None = None
    allowed_entity_types: list[str] | None = None
    policy_source: (
        Literal["enterprise", "cache", "fallback", "local", "package", "unknown"] | None
    ) = None
    policy_cache_hit: bool | None = None
    policy_cache_stale: bool | None = None
    policy_provider_latency_ms: float | None = None


class RehydrationDiagnostic(BaseModel):
    token: str
    entity_type: str | None = None
    status: Literal[
        "allowed",
        "denied",
        "expired",
        "missing_mapping",
        "wrong_scope",
        "policy_blocked",
    ]
    reason: str
    policy_id: str | None = None
    policy_version: str | None = None
    policy_source: Literal["enterprise", "cache", "fallback", "local", "package", "unknown"] = (
        "unknown"
    )
    rule_id: str | None = None
    requester_roles: list[str] = Field(default_factory=list)
    required_roles: list[str] = Field(default_factory=list)
    purpose: str | None = None
    direction: str | None = None
    environment: str | None = None
    token_age_seconds: float | None = None
    max_token_age_seconds: int | None = None
    matched_constraints: dict[str, str] = Field(default_factory=dict)


class RehydrateResponse(BaseModel):
    request_id: str
    text: str
    diagnostics: list[RehydrationDiagnostic] = Field(default_factory=list)
    audit_event: AuditEvent


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatRequest(BaseModel):
    tenant_id: str
    app_id: str
    session_id: str
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    request_id: str
    message: ChatMessage
    audit_event: AuditEvent


class OpenAIChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    metadata: dict[str, str] = Field(default_factory=dict)


class OpenAIChatChoiceMessage(BaseModel):
    role: Literal["assistant"]
    content: str


class OpenAIChatChoice(BaseModel):
    index: int
    message: OpenAIChatChoiceMessage
    finish_reason: str = "stop"


class OpenAIChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[OpenAIChatChoice]
    audit_event: AuditEvent | None = None
