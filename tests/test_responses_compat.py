from collections.abc import Iterable

from fastapi.testclient import TestClient
from prism_compiler.providers import ProviderResponse
from prism_compiler.schemas import ChatMessage, ResponsesInputMessage, ResponsesRequest
from prism_gateway.main import app
from prism_gateway.routes import responses_endpoint
from prism_vault_core import GLOBAL_VAULT
from pytest import MonkeyPatch


class EchoTokenProvider:
    def complete(self, model: str, messages: Iterable[ChatMessage]) -> ProviderResponse:
        latest = ""
        for message in messages:
            latest = message.content
        return ProviderResponse(model=model, content=f"Provider saw {latest}")


def test_p26_responses_route_is_openai_responses_compatible(
    monkeypatch: MonkeyPatch,
) -> None:
    GLOBAL_VAULT.clear()
    monkeypatch.setenv("PRISM_PROVIDER", "mock")
    client = TestClient(app)

    response = client.post(
        "/v1/responses",
        json={
            "model": "mock",
            "instructions": "Be concise",
            "input": "John Smith emailed john@email.com",
            "metadata": {
                "tenant_id": "tenant_dev",
                "app_id": "pulse",
                "session_id": "session_1",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "response"
    assert body["model"] == "mock"
    assert body["output"][0]["type"] == "message"
    assert body["output"][0]["content"][0]["type"] == "output_text"
    assert body["output_text"] == "Mock response for: John Smith emailed john@email.com"


def test_p26_responses_endpoint_transforms_provider_input_and_rehydrates_output() -> None:
    GLOBAL_VAULT.clear()

    response = responses_endpoint(
        ResponsesRequest(
            model="mock",
            input="John Smith emailed john@email.com",
            metadata={
                "tenant_id": "tenant_dev",
                "app_id": "pulse",
                "session_id": "session_1",
            },
        ),
        provider=EchoTokenProvider(),
    )

    assert response.output_text == "Provider saw John Smith emailed john@email.com"
    assert response.output[0].content[0].text == response.output_text
    assert response.audit_event is not None
    assert response.audit_event.event_type == "responses"


def test_p26_responses_endpoint_accepts_message_list_input() -> None:
    GLOBAL_VAULT.clear()

    response = responses_endpoint(
        ResponsesRequest(
            model="mock",
            input=[
                ResponsesInputMessage(role="user", content="John Smith emailed john@email.com"),
                ResponsesInputMessage(role="assistant", content="Acknowledged"),
                ResponsesInputMessage(role="user", content="Call 555-123-4567"),
            ],
            metadata={
                "tenant_id": "tenant_dev",
                "app_id": "pulse",
                "session_id": "session_2",
            },
        ),
        provider=EchoTokenProvider(),
    )

    assert response.output_text == "Provider saw Call 555-123-4567"
