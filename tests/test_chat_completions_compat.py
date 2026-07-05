from fastapi.testclient import TestClient
from prism_gateway.main import app
from prism_vault_core import GLOBAL_VAULT
from pytest import MonkeyPatch


def test_phase4_openai_compatible_chat_completions(monkeypatch: MonkeyPatch) -> None:
    GLOBAL_VAULT.clear()
    monkeypatch.setenv("PRISM_PROVIDER", "mock")
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mock",
            "messages": [
                {
                    "role": "user",
                    "content": "John Smith emailed john@email.com",
                }
            ],
            "metadata": {
                "tenant_id": "tenant_dev",
                "app_id": "pulse",
                "session_id": "session_1",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["model"] == "mock"
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert body["choices"][0]["message"]["content"] == (
        "Mock response for: John Smith emailed john@email.com"
    )
