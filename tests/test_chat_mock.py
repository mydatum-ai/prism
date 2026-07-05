from fastapi.testclient import TestClient
from prism_gateway.main import app
from prism_vault_core import GLOBAL_VAULT


def test_phase1_chat_mock_transforms_and_rehydrates() -> None:
    GLOBAL_VAULT.clear()
    client = TestClient(app)

    response = client.post(
        "/v1/chat/mock",
        json={
            "tenant_id": "tenant_dev",
            "app_id": "pulse",
            "session_id": "session_1",
            "messages": [
                {
                    "role": "user",
                    "content": "John Smith emailed john@email.com about INV-1001",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"]["role"] == "assistant"
    assert body["message"]["content"] == (
        "Mock response for: John Smith emailed john@email.com about INV-1001"
    )
