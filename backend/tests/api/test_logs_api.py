from tests.factories import criar_titulo_aprovado, pagar


def test_logs_registram_o_ciclo_de_vida_do_titulo(client, db):
    titulo = criar_titulo_aprovado(db, valor="100.00")
    pagar(db, titulo, "100.00")

    logs = client.get(f"/titulos/{titulo.id}/logs").json()

    assert [log["tipo"] for log in logs] == [
        "CRIACAO",
        "RATEIO",
        "MUDANCA_STATUS",  # PENDENTE -> APROVADO
        "PAGAMENTO",
        "MUDANCA_STATUS",  # APROVADO -> PAGO
    ]
    assert all(log["status"] == "SUCESSO" for log in logs)


def test_logs_de_titulo_inexistente_retorna_404(client):
    assert client.get("/titulos/999999/logs").status_code == 404
