# AP Copilot

Módulo simplificado de **Títulos a Pagar** com um Copilot de IA (em construção), desenvolvido como projeto de portfólio.

O objetivo não é ser um ERP: é um sistema pequeno, com regras de negócio reais e bem testadas, que serve de base para demonstrar engenharia de IA aplicada — tool calling, RAG, embeddings e agentes — **sem** abrir mão de segurança: o LLM nunca acessa o banco nem executa SQL, apenas chama ferramentas explícitas da aplicação.

> **Status:** Fase 1 concluída (backend financeiro). Veja o [roadmap](#roadmap).

---

## Stack

| Camada | Tecnologias |
|---|---|
| API | Python 3.12, FastAPI, Pydantic v2 |
| Persistência | PostgreSQL 16 (imagem com pgvector), SQLAlchemy 2.0, Alembic |
| Qualidade | pytest (contra Postgres real), Ruff |
| Infra | Docker, Docker Compose, uv |

## Como executar

Pré-requisito: Docker com Docker Compose.

```bash
docker compose up -d --build                       # sobe Postgres + API (aplica migrations)
docker compose exec api python -m scripts.seed     # popula com dados sintéticos
```

- API: http://localhost:8000
- Documentação interativa (OpenAPI): http://localhost:8000/docs

```bash
docker compose exec api pytest                     # testes
docker compose exec api ruff check .               # lint
docker compose exec api python -m scripts.seed --reset   # recria os dados
```

As variáveis de ambiente têm defaults no `docker-compose.yml`; para alterá-las, copie `.env.example` para `.env`.

---

## Arquitetura

```
HTTP ──► api/routes ──► services ──► repositories ──► PostgreSQL
            │               │
         schemas        exceções de domínio  +  AuditService (LogAuditoria)
        (Pydantic)            │
                    core/error_handlers  →  resposta HTTP padronizada
```

| Camada | Responsabilidade |
|---|---|
| `api/` | Recebe a requisição, valida o formato (Pydantic), chama o service. **Sem regra de negócio.** |
| `schemas/` | Contratos de entrada/saída. Validações de formato (CNPJ, valores positivos, datas). |
| `services/` | **Regras de negócio** e fronteira da transação (cada operação de escrita = um commit). |
| `repositories/` | Acesso a dados (queries). Sem regras, sem commit. |
| `models/` | Entidades ORM e constraints de banco. |
| `core/` | Configuração, sessão de banco, exceções, logging estruturado. |

Fases futuras adicionam `ai/` (providers de LLM), `tools/` (funções que o agente pode chamar — que reutilizam os services) e `rag/`.

### Decisões técnicas

- **Dinheiro em `NUMERIC(14,2)` / `Decimal`**, nunca `float`.
- **Defesa em profundidade** para invariantes: Pydantic (borda) → service (regra) → `CHECK` no banco.
- **Auditoria transacional:** o log é gravado na mesma transação da operação. Se ela falhar, o log também é descartado.
- **Lock de linha (`SELECT … FOR UPDATE`)** em toda alteração de título: dois pagamentos simultâneos não conseguem, juntos, exceder o saldo.
- **Máquina de estados explícita** (`services/status_titulo.py`) e um único ponto de mudança de status (`TituloService.mudar_status`).
- **Erros de domínio com código estável** (`RATEIO_INCOMPLETO`, `TITULO_CANCELADO`…), legíveis por máquina — serão usados pelo Copilot para explicar recusas.
- **Enums como `VARCHAR + CHECK`** em vez de `ENUM` nativo: mais fáceis de evoluir por migration.
- **Testes contra PostgreSQL real**, com schema criado pelas próprias migrations e rollback por teste.
- **SQLAlchemy síncrono:** mais simples de ler e testar; o FastAPI executa rotas síncronas em threadpool.
- **Sem exclusão física** de fornecedores e centros de custo: inativação preserva o histórico.

---

## Domínio

### Ciclo de vida do título

```
PENDENTE ──aprovar──► APROVADO ──(pagamentos = valor_total)──► PAGO
 ▲ │  ▲                   │                                       │
 │ │  └──reprocessar── ERRO ◄── falha de integração               │
 │ └──────cancelar────────┴──► CANCELADO                          │
 └─────────────────────── estorno de pagamento ───────────────────┘
```

- `CANCELADO` é final.
- `PAGO` não aceita novos pagamentos, edição, alteração de rateios nem cancelamento. A única operação permitida é **estornar um pagamento confirmado**, que devolve o título para `PENDENTE` (não para `APROVADO`). Assim, ele precisa ser aprovado de novo antes de receber novos pagamentos.
- Estorno em título `APROVADO` mantém o status e apenas recalcula o saldo.
- Dados e rateios só podem ser alterados em `PENDENTE` ou `ERRO`.

### Regras de negócio

| # | Regra | Onde | Código de erro |
|---|---|---|---|
| 1 | Soma dos rateios ≤ valor do título (também ao reduzir o valor) | `RateioService.adicionar`, `TituloService.atualizar` | `RATEIO_EXCEDE_VALOR_TITULO`, `VALOR_MENOR_QUE_RATEIO` |
| 2 | Título só é PAGO quando pagamentos confirmados = valor total; a quitação é **automática** | `PagamentoService.registrar`, `TituloService._garantir_quitado` | `PAGAMENTOS_NAO_QUITAM_TITULO` |
| 3 | Fornecedor inativo não recebe novos títulos | `TituloService.criar` | `FORNECEDOR_INATIVO` |
| 4 | Centro de custo inativo não recebe novos rateios | `RateioService.adicionar` | `CENTRO_CUSTO_INATIVO` |
| 5 | Título cancelado não recebe pagamentos | `PagamentoService.registrar` | `TITULO_CANCELADO` |
| 6 | Valores negativos não são permitidos | schemas + `CHECK` no banco | HTTP 422 de validação |
| 7 | Toda alteração relevante gera log | `AuditService` (em todos os services) | — |
| + | Aprovação exige rateio de exatamente 100% | `TituloService.aprovar` | `RATEIO_INCOMPLETO` |
| + | Pagamento somente para título APROVADO | `PagamentoService.registrar` | `TITULO_NAO_APROVADO` |
| + | Pagamento não pode exceder o saldo pendente | `PagamentoService.registrar` | `PAGAMENTO_EXCEDE_SALDO` |
| + | Título com pagamentos confirmados não pode ser cancelado | `TituloService.cancelar` | `TITULO_COM_PAGAMENTOS` |
| + | Estorno em título PAGO reabre o título como PENDENTE | `PagamentoService.estornar` | — |
| + | Valor do título não pode ficar abaixo do já pago (título reaberto) | `TituloService.atualizar` | `VALOR_MENOR_QUE_PAGO` |

As regras 8–10 (IA nunca executa SQL, nunca acessa o banco diretamente, só usa tools explícitas) serão garantidas pela arquitetura das fases seguintes: as tools chamam services, não o banco.

### Formato de erro

```json
{
  "error": {
    "code": "RATEIO_INCOMPLETO",
    "message": "Título 3 não pode ser aprovado: rateio cobre 6000.00 de 10000.00 (faltam 4000.00).",
    "details": { "titulo_id": 3, "valor_total": "10000.00", "valor_rateado": "6000.00", "valor_faltante": "4000.00" }
  }
}
```

| HTTP | Significado |
|---|---|
| 404 | Recurso não encontrado |
| 409 | Conflito de unicidade (CNPJ, código, número do título, rateio duplicado) |
| 422 | Regra de negócio violada ou payload inválido |

---

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET/POST | `/fornecedores` | Listar (`?ativo=`) / criar |
| GET/PUT | `/fornecedores/{id}` | Obter / atualizar (inclui ativar/inativar) |
| GET/POST | `/centros-custo` | Listar (`?ativo=`) / criar |
| GET/PUT | `/centros-custo/{id}` | Obter / atualizar |
| GET | `/titulos` | Listar (`?status=&fornecedor_id=&vencidos=true&limit=&offset=`) |
| POST | `/titulos` | Criar (status inicial `PENDENTE`) |
| GET | `/titulos/{id}` | Detalhe com resumo financeiro (`valor_rateado`, `valor_pago`, `saldo_pendente`, `vencido`) |
| PUT | `/titulos/{id}` | Atualizar dados (somente `PENDENTE`/`ERRO`) |
| POST | `/titulos/{id}/aprovar` | Aprovar (exige rateio de 100%) |
| POST | `/titulos/{id}/cancelar` | Cancelar (exige `motivo`) |
| POST | `/titulos/{id}/reprocessar` | `ERRO` → `PENDENTE` |
| GET/POST | `/titulos/{id}/rateios` | Listar / adicionar rateio |
| DELETE | `/titulos/{id}/rateios/{rateio_id}` | Remover rateio |
| GET/POST | `/titulos/{id}/pagamentos` | Listar / registrar pagamento |
| POST | `/titulos/{id}/pagamentos/{pagamento_id}/estornar` | Estornar pagamento (título PAGO volta a PENDENTE) |
| GET | `/titulos/{id}/logs` | Trilha de auditoria |

---

## Dados de exemplo

`scripts/seed.py` cria 10 fornecedores, 10 centros de custo e 50 títulos usando os próprios services (os dados respeitam as regras e geram auditoria). As datas são relativas ao dia da execução. Os cenários problemáticos usam a numeração `NF-9xxx`:

| Título | Cenário |
|---|---|
| NF-9001 | Vencido (aprovado, nada pago) |
| NF-9002 | Sem rateio — não pode ser aprovado |
| NF-9003 | Parcialmente rateado (60%) — aprovação bloqueada |
| NF-9004 | Erro de integração: centro de custo 1001 inexistente no ERP |
| NF-9005 | Erro de integração: fornecedor não cadastrado no ERP |
| NF-9006 | Título de fornecedor inativo (lançado antes da inativação) |
| NF-9007 | Rateio em centro de custo inativo (1010) |
| NF-9008 | Parcialmente pago |
| NF-9009 | Completamente pago (duas parcelas) |
| NF-9010 | Cancelado |
| NF-9011 | Vencido e parcialmente pago |

---

## Testes

```bash
docker compose exec api pytest
```

- `tests/services/` — regras de negócio (um teste nomeado por regra, ex.: `test_regra1_…`, `test_regra5_…`).
- `tests/api/` — fluxos HTTP de ponta a ponta e formato de erro.
- Rodam contra o banco `ap_copilot_test` (criado automaticamente pelo compose), com o schema gerado pelas migrations e rollback ao fim de cada teste.

---

## Roadmap

| Fase | Escopo | Status |
|---|---|---|
| 1 | Backend financeiro: entidades, regras, CRUD, auditoria, testes, Docker | ✅ |
| 2 | Camada de LLM independente de fornecedor (OpenAI / Anthropic / Gemini), tool calling e structured outputs | ⏳ |
| 3 | RAG: documentação → chunking → embeddings → pgvector, com citação de fontes | ⏳ |
| 4 | Agente Copilot com tools somente leitura | ⏳ |
| 5 | Frontend (React + TypeScript + Tailwind) | ⏳ |
| 6 | Observabilidade, avaliações e hardening | ⏳ |
| 7 | Ações com confirmação explícita do usuário (opcional) | ⏳ |

### Limitações conhecidas (Fase 1)

- Sem autenticação/autorização.
- A integração com ERP é simulada: o status `ERRO` é produzido pelo seed via `TituloService.registrar_erro_integracao`.
- O lock de concorrência em pagamentos não tem teste automatizado multi-conexão (a suíte usa uma transação por teste).
- A imagem Docker inclui as dependências de desenvolvimento, pois os testes rodam no mesmo container.
