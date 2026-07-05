import time

import pytest
from fastapi.testclient import TestClient
from prism_gateway import auth
from prism_gateway.main import app
from prism_gateway.mydatum_security import public_account, validate_claims


def test_auth_me_requires_session() -> None:
    response = TestClient(app).get("/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "not_authenticated"


def test_auth_login_requires_mydatum_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "MYDATUM_ISSUER",
        "MYDATUM_CLIENT_ID",
        "MYDATUM_CLIENT_SECRET",
        "MYDATUM_REDIRECT_URI",
    ):
        monkeypatch.delenv(name, raising=False)

    response = TestClient(app).get("/auth/login")

    assert response.status_code == 503
    assert response.json()["detail"] == "mydatum_not_configured"


def test_mydatum_provider_supports_internal_discovery_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MYDATUM_ISSUER", "http://localhost:8000")
    monkeypatch.setenv("MYDATUM_CLIENT_ID", "client")
    monkeypatch.setenv("MYDATUM_CLIENT_SECRET", "secret")
    monkeypatch.setenv("MYDATUM_REDIRECT_URI", "http://127.0.0.1:8004/auth/callback")
    monkeypatch.setenv(
        "MYDATUM_DISCOVERY_URL",
        "http://host.docker.internal:8000/.well-known/openid-configuration",
    )

    registered: dict[str, object] = {}
    monkeypatch.setattr(auth.oauth, "create_client", lambda _name: None)
    monkeypatch.setattr(auth.oauth, "register", lambda **kwargs: registered.update(kwargs) or object())

    auth.mydatum_provider()

    assert registered["server_metadata_url"] == (
        "http://host.docker.internal:8000/.well-known/openid-configuration"
    )
    assert registered["client_id"] == "client"


def test_mydatum_claims_map_to_prism_tenant() -> None:
    claims = {
        "iss": "http://localhost:8000",
        "aud": "prism",
        "exp": int(time.time()) + 300,
        "nonce": "nonce",
        "sub": "pairwise-subject",
        "tenant_id": "tenant_a",
        "email": "person@example.test",
    }

    validate_claims(claims, issuer="http://localhost:8000", client_id="prism", nonce="nonce")
    account = public_account(claims, "http://localhost:8000", "tenant_dev")

    assert account["tenant_id"] == "tenant_a"
    assert account["subject"] == "pairwise-subject"
