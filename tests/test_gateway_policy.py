from fastapi.testclient import TestClient
from prism_gateway.main import app
from prism_policy_runtime import clear_policy_cache
from prism_vault_core import GLOBAL_VAULT
from pytest import MonkeyPatch


def test_phase3_gateway_uses_policy_path(monkeypatch: MonkeyPatch) -> None:
    GLOBAL_VAULT.clear()
    clear_policy_cache()
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
    assert body["audit_event"]["metadata"]["policy_source"] == "local"


def test_phase_p15_gateway_uses_policy_provider(monkeypatch: MonkeyPatch) -> None:
    GLOBAL_VAULT.clear()
    clear_policy_cache()
    monkeypatch.delenv("PRISM_POLICY_PATH", raising=False)
    monkeypatch.setenv("PRISM_POLICY_PROVIDER", "prism_policy_runtime.testing:StaticPolicyProvider")
    client = TestClient(app)

    response = client.post(
        "/v1/transform",
        json={
            "tenant_id": "tenant_dev",
            "app_id": "pulse",
            "session_id": "session_1",
            "text": "John Smith emailed john@email.com",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["transformed_text"] == "TEST_1 emailed EMAIL_1"
    assert body["audit_event"]["policy_id"] == "pulse"
    assert body["audit_event"]["policy_version"] == "test"
    assert body["audit_event"]["metadata"]["policy_source"] == "enterprise"
    assert body["audit_event"]["metadata"]["policy_cache_hit"] == "false"


def test_phase_p15_gateway_falls_back_when_provider_returns_none(
    monkeypatch: MonkeyPatch,
) -> None:
    GLOBAL_VAULT.clear()
    clear_policy_cache()
    monkeypatch.delenv("PRISM_POLICY_PATH", raising=False)
    monkeypatch.setenv("PRISM_POLICY_PROVIDER", "prism_policy_runtime.testing:NullPolicyProvider")
    client = TestClient(app)

    response = client.post(
        "/v1/transform",
        json={
            "tenant_id": "tenant_dev",
            "app_id": "pulse",
            "session_id": "session_1",
            "text": "John Smith emailed john@email.com",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["transformed_text"] == "PERSON_1 emailed EMAIL_1"
    assert body["audit_event"]["metadata"]["policy_source"] == "fallback"


def test_phase_p17_runtime_status_reports_policy_source(monkeypatch: MonkeyPatch) -> None:
    clear_policy_cache()
    monkeypatch.delenv("PRISM_POLICY_PATH", raising=False)
    monkeypatch.setenv("PRISM_POLICY_PROVIDER", "prism_policy_runtime.testing:StaticPolicyProvider")
    client = TestClient(app)

    first = client.get(
        "/v1/policies/runtime/status",
        params={"tenant_id": "tenant_dev", "app_id": "pulse"},
    )
    second = client.get(
        "/v1/policies/runtime/status",
        params={"tenant_id": "tenant_dev", "app_id": "pulse"},
    )

    assert first.status_code == 200
    assert first.json()["policy_source"] == "enterprise"
    assert first.json()["policy_cache_hit"] is False
    assert second.status_code == 200
    assert second.json()["policy_source"] == "cache"
    assert second.json()["policy_cache_hit"] is True


def test_runtime_diagnostics_reports_fallback_warning(monkeypatch: MonkeyPatch) -> None:
    clear_policy_cache()
    monkeypatch.delenv("PRISM_POLICY_PATH", raising=False)
    monkeypatch.setenv("PRISM_POLICY_PROVIDER", "prism_policy_runtime.testing:NullPolicyProvider")
    client = TestClient(app)

    response = client.get(
        "/v1/policies/runtime/diagnostics",
        params={"tenant_id": "tenant_dev", "app_id": "pulse"},
    )

    assert response.status_code == 200
    assert response.json()["policy_source"] == "fallback"
    assert response.json()["diagnostics"] == ["using_fallback_policy"]
