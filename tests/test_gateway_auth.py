from fastapi.testclient import TestClient
from prism_gateway.main import app
from prism_policy_runtime import clear_policy_cache, resolve_policy
from prism_policy_runtime.testing import StaticPolicyProvider
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


def test_gateway_policy_cache_invalidation_requires_tenant_scope(
    monkeypatch: MonkeyPatch,
) -> None:
    clear_policy_cache()
    monkeypatch.setenv("PRISM_API_KEYS", "tenant_a:secret-a,tenant_b:secret-b")
    monkeypatch.setenv("PRISM_POLICY_CACHE_TTL_SECONDS", "60")
    resolve_policy("tenant_a", "pulse", provider=StaticPolicyProvider())
    client = TestClient(app)

    denied = client.post(
        "/v1/policies/cache/invalidate",
        headers={"X-Prism-Tenant": "tenant_b", "X-Prism-API-Key": "secret-b"},
        json={"tenant_id": "tenant_a", "app_id": "pulse"},
    )
    allowed = client.post(
        "/v1/policies/cache/invalidate",
        headers={"X-Prism-Tenant": "tenant_a", "X-Prism-API-Key": "secret-a"},
        json={"tenant_id": "tenant_a", "app_id": "pulse"},
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["removed"] == 1
