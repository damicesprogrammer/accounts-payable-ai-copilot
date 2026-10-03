from tests.factories import criar_centro_custo, criar_titulo


def test_fluxo_rateio_e_aprovacao(client, db):
    titulo = criar_titulo(db, valor="1000.00")
    centro = criar_centro_custo(db, codigo="1001")

    response = client.post(
        f"/titulos/{titulo.id}/rateios", json={"centro_custo_id": centro.id, "valor": "1000.00"}
    )
    assert response.status_code == 201
    assert response.json()["centro_custo"]["codigo"] == "1001"

    rateios = client.get(f"/titulos/{titulo.id}/rateios").json()
    assert [r["valor"] for r in rateios] == ["1000.00"]

    response = client.post(f"/titulos/{titulo.id}/aprovar")
    assert response.json()["status"] == "APROVADO"


def test_rateio_excedente_retorna_422_com_detalhes(client, db):
    titulo = criar_titulo(db, valor="100.00")
    centro = criar_centro_custo(db)

    response = client.post(
        f"/titulos/{titulo.id}/rateios", json={"centro_custo_id": centro.id, "valor": "100.01"}
    )

    assert response.status_code == 422
    erro = response.json()["error"]
    assert erro["code"] == "RATEIO_EXCEDE_VALOR_TITULO"
    assert erro["details"]["valor_disponivel"] == "100.00"


def test_aprovar_sem_rateio_completo_retorna_422(client, db):
    titulo = criar_titulo(db)

    response = client.post(f"/titulos/{titulo.id}/aprovar")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RATEIO_INCOMPLETO"


def test_remover_rateio_retorna_204(client, db):
    titulo = criar_titulo(db)
    centro = criar_centro_custo(db)
    rateio = client.post(
        f"/titulos/{titulo.id}/rateios", json={"centro_custo_id": centro.id, "valor": "10.00"}
    ).json()

    response = client.delete(f"/titulos/{titulo.id}/rateios/{rateio['id']}")

    assert response.status_code == 204
