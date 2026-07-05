from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class EntityDetection(BaseModel):
    text: str
    entity_type: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    metadata: dict[str, str] = Field(default_factory=dict)


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


class TransformResponse(BaseModel):
    request_id: str
    transformed_text: str
    detections: list[EntityDetection] = Field(default_factory=list)
    audit_event: AuditEvent


class RehydrateRequest(BaseModel):
    tenant_id: str
    app_id: str
    session_id: str
    text: str


class RehydrateResponse(BaseModel):
    request_id: str
    text: str
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
