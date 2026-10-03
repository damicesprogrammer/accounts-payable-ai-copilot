from tests.factories import criar_centro_custo


def test_crud_centro_custo(client):
    response = client.post("/centros-custo", json={"codigo": "1001", "descricao": "Financeiro"})
    assert response.status_code == 201
    centro_id = response.json()["id"]

    response = client.put(
        f"/centros-custo/{centro_id}", json={"descricao": "Financeiro Corporativo", "ativo": False}
    )
    assert response.status_code == 200
    assert response.json()["ativo"] is False

    response = client.get(f"/centros-custo/{centro_id}")
    assert response.json()["descricao"] == "Financeiro Corporativo"


def test_codigo_duplicado_retorna_409(client, db):
    criar_centro_custo(db, codigo="2002")

    response = client.post("/centros-custo", json={"codigo": "2002", "descricao": "X"})

    assert response.status_code == 409
