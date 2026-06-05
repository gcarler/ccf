def test_healthcheck(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_message(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
