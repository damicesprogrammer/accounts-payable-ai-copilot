def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_e_propagado(client):
    response = client.get("/health", headers={"X-Request-ID": "abc123"})

    assert response.headers["X-Request-ID"] == "abc123"
