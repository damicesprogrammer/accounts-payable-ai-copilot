from tests.factories import criar_fornecedor


def test_criar_e_obter_fornecedor(client):
    response = client.post(
        "/fornecedores", json={"nome": "ACME Ltda", "cnpj": "11.222.333/0001-81"}
    )
    assert response.status_code == 201
    criado = response.json()

    response = client.get(f"/fornecedores/{criado['id']}")
    assert response.status_code == 200
    assert response.json()["cnpj"] == "11222333000181"


def test_cnpj_duplicado_retorna_409_com_codigo(client, db):
    existente = criar_fornecedor(db)

    response = client.post("/fornecedores", json={"nome": "Outro", "cnpj": existente.cnpj})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CNPJ_DUPLICADO"


def test_fornecedor_inexistente_retorna_404(client):
    response = client.get("/fornecedores/999999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FORNECEDOR_NAO_ENCONTRADO"


def test_listar_filtrando_inativos(client, db):
    criar_fornecedor(db, ativo=True)
    inativo = criar_fornecedor(db, ativo=False)

    response = client.get("/fornecedores", params={"ativo": False})

    assert [f["id"] for f in response.json()] == [inativo.id]


def test_campos_desconhecidos_sao_rejeitados(client):
    response = client.post(
        "/fornecedores",
        json={"nome": "X", "cnpj": "11.222.333/0001-81", "ativo": False},
    )

    assert response.status_code == 422
