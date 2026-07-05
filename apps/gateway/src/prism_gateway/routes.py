from uuid import uuid4

from prism_compiler.schemas import (
    AuditEvent,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    RehydrateRequest,
    RehydrateResponse,
    TransformRequest,
    TransformResponse,
)
from prism_rehydration import rehydrate
from prism_transformers import transform


def transform_endpoint(request: TransformRequest) -> TransformResponse:
    return transform(request)


def rehydrate_endpoint(request: RehydrateRequest) -> RehydrateResponse:
    return rehydrate(request)


def chat_mock_endpoint(request: ChatRequest) -> ChatResponse:
    transformed_messages = [
        transform(
            TransformRequest(
                tenant_id=request.tenant_id,
                app_id=request.app_id,
                session_id=request.session_id,
                text=message.content,
            )
        )
        for message in request.messages
    ]
    latest_content = transformed_messages[-1].transformed_text if transformed_messages else ""
    provider_text = f"Mock response for: {latest_content}"
    rehydrated = rehydrate(
        RehydrateRequest(
            tenant_id=request.tenant_id,
            app_id=request.app_id,
            session_id=request.session_id,
            text=provider_text,
        )
    )
    request_id = str(uuid4())
    return ChatResponse(
        request_id=request_id,
        message=ChatMessage(role="assistant", content=rehydrated.text),
        audit_event=AuditEvent(
            event_type="chat.mock",
            tenant_id=request.tenant_id,
            app_id=request.app_id,
            session_id=request.session_id,
            request_id=request_id,
        ),
    )
