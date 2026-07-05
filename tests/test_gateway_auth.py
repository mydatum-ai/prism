from fastapi.testclient import TestClient
from prism_gateway.main import app
from pytest import MonkeyPatch


def test_gateway_accepts_matching_tenant_api_key(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PRISM_API_KEYS", "tenant_a:secret-a")
    client = TestClient(app)

    response = client.post(
        "/v1/transform",
        headers={"X-Prism-Tenant": "tenant_a", "X-Prism-API-Key": "secret-a"},
        json={
            "tenant_id": "tenant_a",
            "app_id": "pulse",
            "session_id": "s1",
            "text": "Email maria@example.com",
        },
    )

    assert response.status_code == 200
    assert response.json()["audit_event"]["tenant_id"] == "tenant_a"


def test_gateway_rejects_cross_tenant_body(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("PRISM_API_KEYS", "tenant_a:secret-a")
    client = TestClient(app)

    response = client.post(
        "/v1/transform",
        headers={"X-Prism-Tenant": "tenant_a", "X-Prism-API-Key": "secret-a"},
        json={
            "tenant_id": "tenant_b",
            "app_id": "pulse",
            "session_id": "s1",
            "text": "Email maria@example.com",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "tenant_scope_mismatch"
