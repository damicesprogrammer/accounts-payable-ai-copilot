from tests.factories import criar_titulo, criar_titulo_aprovado


def test_fluxo_completo_ate_pago(client, db):
    titulo = criar_titulo_aprovado(db, valor="1000.00")
    data = titulo.data_emissao.isoformat()

    r1 = client.post(
        f"/titulos/{titulo.id}/pagamentos", json={"data_pagamento": data, "valor": "250.00"}
    )
    r2 = client.post(
        f"/titulos/{titulo.id}/pagamentos", json={"data_pagamento": data, "valor": "750.00"}
    )

    assert r1.status_code == r2.status_code == 201
    assert client.get(f"/titulos/{titulo.id}").json()["status"] == "PAGO"
    assert len(client.get(f"/titulos/{titulo.id}/pagamentos").json()) == 2


def test_pagamento_em_titulo_pendente_retorna_422(client, db):
    titulo = criar_titulo(db)

    response = client.post(
        f"/titulos/{titulo.id}/pagamentos",
        json={"data_pagamento": titulo.data_emissao.isoformat(), "valor": "10.00"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "TITULO_NAO_APROVADO"


def test_pagamento_negativo_e_rejeitado(client, db):
    titulo = criar_titulo_aprovado(db)

    response = client.post(
        f"/titulos/{titulo.id}/pagamentos",
        json={"data_pagamento": titulo.data_emissao.isoformat(), "valor": "-5.00"},
    )

    assert response.status_code == 422


def test_estornar_pagamento(client, db):
    titulo = criar_titulo_aprovado(db)
    pagamento = client.post(
        f"/titulos/{titulo.id}/pagamentos",
        json={"data_pagamento": titulo.data_emissao.isoformat(), "valor": "10.00"},
    ).json()

    response = client.post(f"/titulos/{titulo.id}/pagamentos/{pagamento['id']}/estornar")

    assert response.status_code == 200
    assert response.json()["status"] == "ESTORNADO"
