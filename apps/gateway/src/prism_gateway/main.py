from typing import Annotated

from fastapi import Depends, FastAPI
from prism_compiler.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    RehydrateRequest,
    RehydrateResponse,
    TransformRequest,
    TransformResponse,
)

from prism_gateway.auth import Principal, authenticate, require_tenant
from prism_gateway.routes import (
    chat_completions_endpoint,
    chat_mock_endpoint,
    rehydrate_endpoint,
    transform_endpoint,
)
from prism_gateway.storage import active_audit_store

app = FastAPI(
    title="Prism Gateway",
    version="0.1.0",
    description="Open-core privacy transformation gateway.",
)


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service="prism-gateway")


@app.post("/v1/transform", response_model=TransformResponse)
def transform_route(
    request: TransformRequest,
    principal: Annotated[Principal, Depends(authenticate)],
) -> TransformResponse:
    require_tenant(principal, request.tenant_id)
    response = transform_endpoint(request)
    active_audit_store().record(response.audit_event)
    return response


@app.post("/v1/rehydrate", response_model=RehydrateResponse)
def rehydrate_route(
    request: RehydrateRequest,
    principal: Annotated[Principal, Depends(authenticate)],
) -> RehydrateResponse:
    require_tenant(principal, request.tenant_id)
    response = rehydrate_endpoint(request)
    active_audit_store().record(response.audit_event)
    return response


@app.post("/v1/chat/mock", response_model=ChatResponse)
def chat_mock_route(
    request: ChatRequest,
    principal: Annotated[Principal, Depends(authenticate)],
) -> ChatResponse:
    require_tenant(principal, request.tenant_id)
    response = chat_mock_endpoint(request)
    active_audit_store().record(response.audit_event)
    return response


@app.post("/v1/chat/completions", response_model=OpenAIChatCompletionResponse)
def chat_completions_route(
    request: OpenAIChatCompletionRequest,
    principal: Annotated[Principal, Depends(authenticate)],
) -> OpenAIChatCompletionResponse:
    tenant_id = request.metadata.get("tenant_id", "default")
    require_tenant(principal, tenant_id)
    response = chat_completions_endpoint(request)
    if response.audit_event is not None:
        active_audit_store().record(response.audit_event)
    return response


@app.get("/v1/audit/{tenant_id}")
def audit_route(
    tenant_id: str,
    principal: Annotated[Principal, Depends(authenticate)],
) -> dict[str, object]:
    require_tenant(principal, tenant_id)
    return {"tenant_id": tenant_id, "events": active_audit_store().list_for_tenant(tenant_id)}
