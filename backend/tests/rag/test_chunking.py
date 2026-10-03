from pathlib import Path

from app.rag.chunking import LIMITE_CARACTERES, Chunk, carregar_chunks, dividir_em_secoes

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"

MARKDOWN = """\
Texto antes de qualquer heading é ignorado.

# Pagamentos

## Registro

Pagamento só em título APROVADO.

## Estorno

Estorno de título PAGO volta para PENDENTE.

Segundo parágrafo do estorno.
"""


def test_markdown_e_separado_por_secoes_preservando_source_e_section():
    chunks = dividir_em_secoes("regras_pagamentos.md", MARKDOWN)

    assert chunks == [
        Chunk("regras_pagamentos.md", "Registro", "Pagamento só em título APROVADO."),
        Chunk(
            "regras_pagamentos.md",
            "Estorno",
            "Estorno de título PAGO volta para PENDENTE.\n\nSegundo parágrafo do estorno.",
        ),
    ]  # "# Pagamentos" não tem texto próprio e não gera chunk


def test_heading_dentro_de_bloco_de_codigo_nao_inicia_secao():
    markdown = "## Fluxo\n\n```\n# isto é código\nPENDENTE -> APROVADO\n```\n"

    [chunk] = dividir_em_secoes("manual.md", markdown)

    assert chunk.section == "Fluxo"
    assert "# isto é código" in chunk.content


def test_secao_grande_e_dividida_por_paragrafos_mantendo_a_secao():
    paragrafo = "palavra " * 150  # ~1200 caracteres
    markdown = "## Grande\n\n" + "\n\n".join([paragrafo.strip()] * 3)

    chunks = dividir_em_secoes("grande.md", markdown)

    assert len(chunks) == 3
    assert {c.section for c in chunks} == {"Grande"}
    assert all(len(c.content) <= LIMITE_CARACTERES for c in chunks)


def test_documentos_da_base_de_conhecimento_geram_chunks():
    chunks = carregar_chunks(DOCS_DIR)

    assert {c.source for c in chunks} == {
        "regras_titulos.md",
        "regras_rateios.md",
        "regras_pagamentos.md",
        "erros_integracao.md",
        "manual_financeiro.md",
    }
    assert all(c.section and c.content for c in chunks)
    # Documentos pequenos de propósito: nenhuma seção precisa ser dividida.
    assert all(len(c.content) <= LIMITE_CARACTERES for c in chunks)
    secoes = {(c.source, c.section) for c in chunks}
    assert ("regras_pagamentos.md", "Estorno de título PAGO") in secoes
    assert len(secoes) == len(chunks)  # cada (source, section) identifica um chunk
