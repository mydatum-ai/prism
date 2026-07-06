import os
import time
from uuid import uuid4

from fastapi import HTTPException
from prism_compiler.providers import MockProvider, OpenAIProvider, Provider
from prism_compiler.schemas import (
    AuditEvent,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    OpenAIChatChoice,
    OpenAIChatChoiceMessage,
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    RehydrateRequest,
    RehydrateResponse,
    RuntimePolicyStatusResponse,
    TransformRequest,
    TransformResponse,
)
from prism_policy_runtime import (
    DEFAULT_POLICY,
    Policy,
    PolicyResolution,
    resolve_policy_with_metadata,
)
from prism_rehydration import rehydrate
from prism_transformers import transform


def active_policy_resolution(
    tenant_id: str = "default", app_id: str = "default"
) -> PolicyResolution:
    try:
        return resolve_policy_with_metadata(tenant_id, app_id, fallback=DEFAULT_POLICY)
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


def active_policy(tenant_id: str = "default", app_id: str = "default") -> Policy:
    return active_policy_resolution(tenant_id, app_id).policy


def runtime_policy_status(
    tenant_id: str,
    app_id: str,
) -> RuntimePolicyStatusResponse:
    resolution = active_policy_resolution(tenant_id, app_id)
    diagnostics: list[str] = []
    if resolution.source == "fallback":
        diagnostics.append("using_fallback_policy")
    if resolution.cache_stale:
        diagnostics.append("using_stale_cached_policy")
    return RuntimePolicyStatusResponse(
        tenant_id=tenant_id,
        app_id=app_id,
        policy_id=resolution.policy.policy_id,
        policy_version=resolution.policy.version,
        policy_source=resolution.source,
        policy_cache_hit=resolution.cache_hit,
        policy_cache_stale=resolution.cache_stale,
        policy_provider_latency_ms=resolution.provider_latency_ms,
        diagnostics=diagnostics,
    )


def policy_audit_metadata(resolution: PolicyResolution) -> dict[str, str]:
    return {
        "policy_source": resolution.source,
        "policy_cache_hit": str(resolution.cache_hit).lower(),
        "policy_cache_stale": str(resolution.cache_stale).lower(),
        "policy_provider_latency_ms": f"{resolution.provider_latency_ms:.3f}",
    }


def request_with_policy_metadata(
    request: TransformRequest | RehydrateRequest,
    resolution: PolicyResolution,
) -> TransformRequest | RehydrateRequest:
    return request.model_copy(
        update={
            "policy_source": resolution.source,
            "policy_cache_hit": resolution.cache_hit,
            "policy_cache_stale": resolution.cache_stale,
            "policy_provider_latency_ms": resolution.provider_latency_ms,
        }
    )


def active_provider() -> Provider:
    provider_name = os.getenv("PRISM_PROVIDER", "mock").lower()
    if provider_name == "mock":
        return MockProvider()
    if provider_name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY is required")
        base_url = os.getenv("PRISM_OPENAI_BASE_URL", "https://api.openai.com/v1")
        return OpenAIProvider(api_key=api_key, base_url=base_url)
    raise HTTPException(status_code=500, detail=f"Unsupported provider: {provider_name}")


def transform_endpoint(request: TransformRequest) -> TransformResponse:
    resolution = active_policy_resolution(request.tenant_id, request.app_id)
    enriched_request = request_with_policy_metadata(request, resolution)
    assert isinstance(enriched_request, TransformRequest)
    response = transform(enriched_request, policy=resolution.policy)
    response.audit_event.metadata.update(policy_audit_metadata(resolution))
    return response


def rehydrate_endpoint(request: RehydrateRequest) -> RehydrateResponse:
    resolution = active_policy_resolution(request.tenant_id, request.app_id)
    enriched_request = request_with_policy_metadata(request, resolution)
    assert isinstance(enriched_request, RehydrateRequest)
    response = rehydrate(enriched_request, policy=resolution.policy)
    response.audit_event.metadata.update(policy_audit_metadata(resolution))
    return response


def chat_mock_endpoint(request: ChatRequest) -> ChatResponse:
    resolution = active_policy_resolution(request.tenant_id, request.app_id)
    transformed_messages = [
        transform(
            TransformRequest(
                tenant_id=request.tenant_id,
                app_id=request.app_id,
                session_id=request.session_id,
                text=message.content,
                policy_source=resolution.source,
                policy_cache_hit=resolution.cache_hit,
                policy_cache_stale=resolution.cache_stale,
                policy_provider_latency_ms=resolution.provider_latency_ms,
            ),
            policy=resolution.policy,
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
            policy_source=resolution.source,
            policy_cache_hit=resolution.cache_hit,
            policy_cache_stale=resolution.cache_stale,
            policy_provider_latency_ms=resolution.provider_latency_ms,
        ),
        policy=resolution.policy,
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
            policy_id=resolution.policy.policy_id,
            policy_version=resolution.policy.version,
            metadata=policy_audit_metadata(resolution),
        ),
    )


def chat_completions_endpoint(
    request: OpenAIChatCompletionRequest,
    provider: Provider | None = None,
) -> OpenAIChatCompletionResponse:
    tenant_id = request.metadata.get("tenant_id", "default")
    app_id = request.metadata.get("app_id", "default")
    session_id = request.metadata.get("session_id", str(uuid4()))
    resolution = active_policy_resolution(tenant_id, app_id)
    transformed_messages = [
        ChatMessage(
            role=message.role,
            content=transform(
                TransformRequest(
                    tenant_id=tenant_id,
                    app_id=app_id,
                    session_id=session_id,
                    text=message.content,
                    policy_source=resolution.source,
                    policy_cache_hit=resolution.cache_hit,
                    policy_cache_stale=resolution.cache_stale,
                    policy_provider_latency_ms=resolution.provider_latency_ms,
                ),
                policy=resolution.policy,
            ).transformed_text,
        )
        for message in request.messages
    ]
    provider_response = (provider or active_provider()).complete(
        request.model, transformed_messages
    )
    rehydrated = rehydrate(
        RehydrateRequest(
            tenant_id=tenant_id,
            app_id=app_id,
            session_id=session_id,
            text=provider_response.content,
            policy_source=resolution.source,
            policy_cache_hit=resolution.cache_hit,
            policy_cache_stale=resolution.cache_stale,
            policy_provider_latency_ms=resolution.provider_latency_ms,
        ),
        policy=resolution.policy,
    )
    return OpenAIChatCompletionResponse(
        id=f"chatcmpl-{uuid4().hex}",
        created=int(time.time()),
        model=provider_response.model,
        choices=[
            OpenAIChatChoice(
                index=0,
                message=OpenAIChatChoiceMessage(role="assistant", content=rehydrated.text),
            )
        ],
        audit_event=AuditEvent(
            event_type="chat.completions",
            tenant_id=tenant_id,
            app_id=app_id,
            session_id=session_id,
            request_id=rehydrated.request_id,
            policy_id=resolution.policy.policy_id,
            policy_version=resolution.policy.version,
            metadata=policy_audit_metadata(resolution),
        ),
    )
