from fastapi.testclient import TestClient
from prism_gateway.main import app


def test_healthz() -> None:
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "prism-gateway"}
