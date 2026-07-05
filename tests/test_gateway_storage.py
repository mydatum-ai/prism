from pathlib import Path

from fastapi.testclient import TestClient
from prism_gateway.main import app
from pytest import MonkeyPatch


def test_gateway_persists_tenant_scoped_audit_events(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PRISM_AUDIT_DB", str(tmp_path / "audit.sqlite3"))
    monkeypatch.setenv("PRISM_API_KEYS", "tenant_a:secret-a,tenant_b:secret-b")
    client = TestClient(app)

    response = client.post(
        "/v1/transform",
        headers={"X-Prism-Tenant": "tenant_a", "X-Prism-API-Key": "secret-a"},
        json={
            "tenant_id": "tenant_a",
            "app_id": "pulse",
            "session_id": "s1",
            "text": "Maria emailed maria@example.com",
        },
    )
    assert response.status_code == 200

    audit = client.get(
        "/v1/audit/tenant_a",
        headers={"X-Prism-Tenant": "tenant_a", "X-Prism-API-Key": "secret-a"},
    )

    assert audit.status_code == 200
    assert audit.json()["tenant_id"] == "tenant_a"
    assert audit.json()["events"][0]["event_type"] == "transform"

    cross_tenant = client.get(
        "/v1/audit/tenant_a",
        headers={"X-Prism-Tenant": "tenant_b", "X-Prism-API-Key": "secret-b"},
    )
    assert cross_tenant.status_code == 403
