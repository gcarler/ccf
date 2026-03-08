from fastapi.testclient import TestClient

from backend.app import app


client = TestClient(app)


def test_healthcheck():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_message():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
