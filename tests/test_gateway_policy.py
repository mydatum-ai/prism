from fastapi.testclient import TestClient
from prism_gateway.main import app
from prism_vault_core import GLOBAL_VAULT
from pytest import MonkeyPatch


def test_phase3_gateway_uses_policy_path(monkeypatch: MonkeyPatch) -> None:
    GLOBAL_VAULT.clear()
    monkeypatch.setenv("PRISM_POLICY_PATH", "examples/policies/pulse.yaml")
    client = TestClient(app)

    response = client.post(
        "/v1/transform",
        json={
            "tenant_id": "tenant_dev",
            "app_id": "pulse",
            "session_id": "session_1",
            "text": "John Smith emailed john@email.com about INV-1001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["transformed_text"] == "RESIDENT_1 emailed EMAIL_1 about INV-1001"
    assert body["audit_event"]["policy_id"] == "pulse"
