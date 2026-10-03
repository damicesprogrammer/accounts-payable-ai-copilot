from datetime import date, timedelta

from tests.factories import criar_fornecedor, criar_titulo


def _payload(fornecedor_id: int, **overrides) -> dict:
    hoje = date.today()
    return {
        "numero": "NF-500",
        "fornecedor_id": fornecedor_id,
        "descricao": "Licenças de software",
        "data_emissao": hoje.isoformat(),
        "data_vencimento": (hoje + timedelta(days=15)).isoformat(),
        "valor_total": "2500.00",
        **overrides,
    }


def test_criar_obter_e_listar_titulo(client, db):
    fornecedor = criar_fornecedor(db, nome="ACME")

    response = client.post("/titulos", json=_payload(fornecedor.id))
    assert response.status_code == 201
    titulo = response.json()
    assert titulo["status"] == "PENDENTE"
    assert titulo["fornecedor"] == {"id": fornecedor.id, "nome": "ACME"}
    assert titulo["valor_total"] == "2500.00"

    assert client.get(f"/titulos/{titulo['id']}").status_code == 200
    assert [t["id"] for t in client.get("/titulos").json()] == [titulo["id"]]


def test_fornecedor_inativo_retorna_422_com_codigo(client, db):
    fornecedor = criar_fornecedor(db, ativo=False)

    response = client.post("/titulos", json=_payload(fornecedor.id))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FORNECEDOR_INATIVO"


def test_valor_negativo_e_rejeitado_na_borda(client, db):
    fornecedor = criar_fornecedor(db)

    response = client.post("/titulos", json=_payload(fornecedor.id, valor_total="-1.00"))

    assert response.status_code == 422


def test_atualizar_titulo_via_put(client, db):
    titulo = criar_titulo(db)
    payload = _payload(titulo.fornecedor_id, numero=titulo.numero, valor_total="999.90")
    del payload["fornecedor_id"]

    response = client.put(f"/titulos/{titulo.id}", json=payload)

    assert response.status_code == 200
    assert response.json()["valor_total"] == "999.90"


def test_cancelar_exige_motivo(client, db):
    titulo = criar_titulo(db)

    assert client.post(f"/titulos/{titulo.id}/cancelar", json={}).status_code == 422
    response = client.post(f"/titulos/{titulo.id}/cancelar", json={"motivo": "Duplicado"})
    assert response.json()["status"] == "CANCELADO"


def test_filtrar_por_status(client, db):
    criar_titulo(db)
    cancelado = criar_titulo(db)
    client.post(f"/titulos/{cancelado.id}/cancelar", json={"motivo": "x"})

    response = client.get("/titulos", params={"status": "CANCELADO"})

    assert [t["id"] for t in response.json()] == [cancelado.id]


def test_detalhe_expoe_resumo_financeiro(client, db):
    titulo = criar_titulo(db, valor="500.00")

    detalhe = client.get(f"/titulos/{titulo.id}").json()

    assert detalhe["valor_rateado"] == "0.00"
    assert detalhe["saldo_pendente"] == "500.00"
    assert detalhe["vencido"] is False
