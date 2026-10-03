def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_e_propagado(client):
    response = client.get("/health", headers={"X-Request-ID": "abc123"})

    assert response.headers["X-Request-ID"] == "abc123"


def test_cors_libera_somente_o_frontend_local(client):
    permitido = client.get("/health", headers={"Origin": "http://localhost:5173"})
    outro = client.get("/health", headers={"Origin": "http://evil.example"})

    assert permitido.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in outro.headers
