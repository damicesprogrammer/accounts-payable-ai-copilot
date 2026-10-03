"""Chunking por seção Markdown.

Regras (propositalmente simples — os documentos são nossos e pequenos):
- Cada heading (`#` a `######`) inicia uma seção; `section` é o texto do heading.
- Seções sem texto (ex.: o título `# Pagamentos` seguido direto de `## Registro`)
  não geram chunk. Texto antes do primeiro heading é ignorado.
- Linhas dentro de blocos de código (```) nunca são tratadas como heading.
- Seção maior que LIMITE_CARACTERES é dividida nos parágrafos (linhas em branco),
  acumulando parágrafos até o limite; todas as partes mantêm a mesma `section`.
  Um parágrafo sozinho maior que o limite não é cortado.
"""

import re
from dataclasses import dataclass
from pathlib import Path

LIMITE_CARACTERES = 2000

_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")


@dataclass(frozen=True)
class Chunk:
    source: str
    section: str
    content: str


def carregar_chunks(docs_dir: Path) -> list[Chunk]:
    """Lê todos os `*.md` do diretório (em ordem alfabética) e os divide em chunks."""
    chunks: list[Chunk] = []
    for arquivo in sorted(docs_dir.glob("*.md")):
        chunks.extend(dividir_em_secoes(arquivo.name, arquivo.read_text(encoding="utf-8")))
    return chunks


def dividir_em_secoes(source: str, markdown: str) -> list[Chunk]:
    secoes: list[tuple[str, list[str]]] = []
    em_bloco_de_codigo = False

    for linha in markdown.splitlines():
        if linha.lstrip().startswith("```"):
            em_bloco_de_codigo = not em_bloco_de_codigo
        heading = None if em_bloco_de_codigo else _HEADING.match(linha)
        if heading:
            secoes.append((heading.group(1), []))
        elif secoes:
            secoes[-1][1].append(linha)

    return [
        Chunk(source=source, section=titulo, content=parte)
        for titulo, linhas in secoes
        for parte in _limitar("\n".join(linhas).strip())
    ]


def _limitar(texto: str) -> list[str]:
    if not texto:
        return []
    if len(texto) <= LIMITE_CARACTERES:
        return [texto]

    partes: list[str] = []
    atual = ""
    for paragrafo in re.split(r"\n\s*\n", texto):
        candidato = f"{atual}\n\n{paragrafo}" if atual else paragrafo
        if atual and len(candidato) > LIMITE_CARACTERES:
            partes.append(atual)
            atual = paragrafo
        else:
            atual = candidato
    partes.append(atual)
    return partes
