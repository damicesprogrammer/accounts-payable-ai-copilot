# AP Copilot

Módulo simplificado de **Títulos a Pagar** com um Copilot de IA (em construção), desenvolvido como projeto de portfólio.

O objetivo não é ser um ERP: é um sistema pequeno, com regras de negócio reais e bem testadas, que serve de base para demonstrar engenharia de IA aplicada — tool calling, RAG, embeddings e agentes — **sem** abrir mão de segurança: o LLM nunca acessa o banco nem executa SQL, apenas chama ferramentas explícitas da aplicação.

> **Status:** Fases 1 (backend financeiro), 2 (fundação de LLM e tool calling), 3 (RAG com pgvector) e 4 (agent loop) concluídas. Veja o [roadmap](#roadmap).

---

## Stack

| Camada | Tecnologias |
|---|---|
| API | Python 3.12, FastAPI, Pydantic v2 |
| Persistência | PostgreSQL 16 (imagem com pgvector), SQLAlchemy 2.0, Alembic |
| Qualidade | pytest (contra Postgres real), Ruff |
| IA | SDK oficial da OpenAI (atrás de um contrato próprio), Pydantic para structured outputs, pgvector para busca semântica |
| Infra | Docker, Docker Compose, uv |

## Como executar

Pré-requisito: Docker com Docker Compose.

```bash
docker compose up -d --build                       # sobe Postgres + API (aplica migrations)
docker compose exec api python -m scripts.seed     # popula com dados sintéticos
docker compose exec api python -m scripts.index_docs  # indexa a base de conhecimento (requer OPENAI_API_KEY)
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
| `ai/` | Contratos de LLM e embeddings e seus providers (OpenAI e fake para testes). Ver [Camada de IA](#camada-de-ia). |
| `tools/` | Funções que o LLM pode solicitar (allowlist explícita). Chamam services, nunca repositories. |
| `rag/` | RAG manual: chunking por seção Markdown e `RAGService` (indexar, search, answer). Ver [RAG](#rag-base-de-conhecimento). |
| `agent/` | `AgentService`: loop controlado de tool calling. Ver [Agente Copilot](#agente-copilot-agent-loop). |

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

As regras 8–10 (IA nunca executa SQL, nunca acessa o banco diretamente, só usa tools explícitas) são garantidas pela arquitetura: o LLM só pede tools da allowlist, e as tools chamam services, não o banco.

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
| POST | `/ai/ask` | Pergunta sobre as regras do AP Copilot, respondida por RAG com fontes |
| POST | `/ai/copilot` | Copilot: o modelo consulta o sistema e a documentação via tools somente leitura |

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
- `tests/ai/` — providers (fake e OpenAI com cliente substituto: sem rede, sem tokens, sem API key).
- `tests/tools/` — registry, tools financeiras e garantias de segurança.
- `tests/rag/` — chunking, indexação, busca no pgvector e resposta com validação de fontes (embeddings e LLM fake).
- `tests/agent/` — agent loop (roteiros determinísticos com LLM fake) e garantias de segurança do agente.
- Rodam contra o banco `ap_copilot_test` (criado automaticamente pelo compose), com o schema gerado pelas migrations e rollback ao fim de cada teste.

---

## Camada de IA

Blocos fundamentais: contrato de LLM, provider OpenAI, tool calling, structured outputs, embeddings, RAG e o agent loop. **Ainda não há tools de escrita.**

```
LLMProvider.generate(mensagens, tools)      ← contrato próprio (ai/contracts.py)
   └─ OpenAIProvider                        ← único módulo de chat que conhece a SDK
        └─ resposta normalizada: LLMResponse { content, tool_calls: [ToolCall] }

ToolCall ─► ToolRegistry.execute ─► Tool ─► Service ─► Repository ─► PostgreSQL
              │
              ├─ nome fora da allowlist   → TOOL_NAO_PERMITIDA
              ├─ argumentos inválidos     → ARGUMENTOS_INVALIDOS (validação Pydantic)
              ├─ DomainError              → código do domínio (ex.: TITULO_NAO_ENCONTRADO)
              ├─ erro da camada de IA     → IA_INDISPONIVEL (ex.: sem API key)
              └─ erro inesperado          → ERRO_INTERNO (detalhes só no log do servidor)
```

| Arquivo | Conteúdo |
|---|---|
| `ai/contracts.py` | `ChatMessage` (inclui tool calls do assistant e resultados de tools), `ToolDefinition`, `ToolCall`, `LLMResponse`, `TokenUsage` e os `Protocol`s `LLMProvider` e `EmbeddingProvider` |
| `ai/exceptions.py` | `LLMConfigurationError`, `LLMTimeoutError`, `LLMProviderError`, `LLMStructuredOutputError` |
| `ai/providers/openai.py` | Chat: conversão de/para a SDK da OpenAI, tradução de erros, log de metadados |
| `ai/providers/openai_embeddings.py` | Embeddings OpenAI com dimensão fixa (1536) |
| `ai/providers/fake.py` | `FakeLLMProvider` (roteirizado) e `FakeEmbeddingProvider` (determinístico) para testes |
| `ai/providers/__init__.py` | `get_llm_provider()` e `get_embedding_provider()`, a partir da configuração |
| `tools/registry.py` | `ToolRegistry` e `criar_registry_financeiro()`, a allowlist explícita |
| `tools/titulo_tools.py` | As tools de consulta financeira |
| `tools/documentacao_tools.py` | A tool `search_documentation` |

### Tools disponíveis (todas somente leitura)

| Tool | O que usa |
|---|---|
| `get_titulo(titulo_id)` | `TituloService.obter_detalhe`: status, fornecedor, datas, valor total, rateado, pago, saldo e vencido |
| `get_rateios_titulo(titulo_id)` | `RateioService.listar` |
| `get_pagamentos_titulo(titulo_id)` | `PagamentoService.listar` |
| `get_logs_titulo(titulo_id)` | `TituloService.listar_logs` |
| `get_titulos_vencidos()` | `TituloService.listar(vencidos=True)` |
| `search_documentation(query)` | `RAGService.search`: só retrieval (`source`, `section`, `content`, `score`), **não** chama o LLM |

Resultado padronizado, serializável em JSON (valores monetários como string com 2 casas):

```json
{ "ok": true,  "data": { "numero": "NF-9008", "saldo_pendente": "1800.00", "...": "..." }, "error": null }
{ "ok": false, "data": null, "error": { "code": "TITULO_NAO_ENCONTRADO", "message": "Título 999 não encontrado." } }
```

### Structured outputs

`provider.generate_structured(mensagens, response_model=MeuSchema)` devolve uma instância validada de `MeuSchema`. Se a resposta não for compatível, ou se o modelo recusar, lança `LLMStructuredOutputError`. Nunca devolve um objeto parcialmente validado.

### Segurança

- O LLM não acessa o banco nem gera SQL: ele só pode pedir tools pelo nome. O nome serve apenas como chave de um dicionário de tools registradas explicitamente, sem `eval`, `exec`, import dinâmico ou `getattr` sobre texto do modelo.
- Os argumentos são validados por modelos Pydantic com `extra="forbid"` antes de qualquer execução.
- A `query` de `search_documentation` só vira embedding: nunca é interpolada em SQL.
- Testes garantem que a allowlist é exatamente a esperada, que nenhuma tool altera dados (sem flush, sem mudança de estado), que argumentos maliciosos são recusados e que erros internos não vazam detalhes.

### Configuração

| Variável | Descrição |
|---|---|
| `LLM_PROVIDER` | `openai` (único suportado) |
| `OPENAI_API_KEY` | Chave da API. Lida como `SecretStr`: não aparece em `repr`, logs ou respostas |
| `OPENAI_MODEL` | Modelo de chat (obrigatório para chamadas reais) |
| `OPENAI_REASONING_EFFORT` | Opcional. Repassado como `reasoning_effort` quando definido (ex.: `none`); vazio = não enviado |
| `OPENAI_EMBEDDING_MODEL` | Modelo de embeddings (default `text-embedding-3-small`) |

A API financeira sobe e funciona sem essas variáveis; a ausência só gera erro (`LLMConfigurationError`) quando algo que usa o LLM é chamado. Defina-as no `.env` da raiz, que não é versionado.

### Observabilidade

- Cada chamada ao LLM: `provider`, `model`, `duration_ms`, `input_tokens`, `output_tokens`, `finish_reason` e o número de `tool_calls`. Uma chamada recusada ou sem objeto válido é registrada como falha, não como sucesso.
- Cada execução de tool: `tool`, `ok`, `error_code` e `duration_ms`.
- Embeddings: `model`, quantidade de `textos`, `input_tokens` e `duration_ms`.
- Indexação: quantidade de `documentos`, de `chunks` e `duration_ms`. Busca: quantidade de `resultados` e `duration_ms`.
- Prompts, perguntas, respostas e conteúdo dos documentos não são registrados.

### Smoke test manual (opcional)

Com `OPENAI_API_KEY` e `OPENAI_MODEL` configurados (consome tokens; não faz parte do `pytest`):

```bash
docker compose exec api python -m scripts.smoke_openai --titulo-id 4
```

Prova o fluxo: LLM real → solicita tool → `ToolCall` → `ToolRegistry` → service → resultado estruturado.

---

## RAG (base de conhecimento)

RAG implementado manualmente, sem frameworks: o objetivo é deixar cada etapa visível.

```
Indexação (comando explícito)            Pergunta (POST /ai/ask)
─────────────────────────────            ───────────────────────
docs/*.md                                pergunta
  ↓ chunking por seção (heading)           ↓ embedding
chunks                                   pgvector: ORDER BY embedding <=> :q LIMIT 5
  ↓ embeddings (OpenAI)                    ↓
chunks_documentacao (pgvector)           top chunks → contexto numerado
                                           ↓ LLM (structured output)
                                         { answer, sources } → fontes validadas
```

### Base de conhecimento

`backend/docs/` contém documentos fictícios, escritos para o AP Copilot e coerentes com as regras do código: `regras_titulos.md`, `regras_rateios.md`, `regras_pagamentos.md`, `erros_integracao.md` e `manual_financeiro.md`. Os documentos são propositalmente pequenos.

### Tabela

`chunks_documentacao`: `id`, `source` (nome do arquivo), `section` (heading), `content`, `embedding vector(1536)` e `created_at`. Não há tabela de documentos, versionamento nem metadados em JSON. A migration `0003` ativa a extensão `vector`. Não há índice vetorial (HNSW/IVFFlat): com poucas dezenas de linhas, a busca exata por varredura é instantânea e determinística.

### Chunking (`rag/chunking.py`)

- Cada heading Markdown inicia uma seção; `section` é o texto do heading. Headings dentro de blocos de código são ignorados.
- Seções sem texto próprio (ex.: o título `# Pagamentos` seguido direto de `## Registro`) não geram chunk.
- Uma seção com mais de 2.000 caracteres é dividida nos parágrafos, mantendo a mesma `section`. Hoje nenhum documento chega a esse limite.
- O texto vetorizado é `section + content`: o heading resume do que a seção trata.

### Indexação

```bash
docker compose exec api python -m scripts.index_docs
```

Gera os embeddings de todos os chunks **antes** de tocar no banco e então, em uma única transação, apaga os chunks antigos e grava os novos. Se o provider falhar, o banco não é tocado; se a gravação falhar, o rollback preserva o índice anterior. Não há indexação incremental, hash de conteúdo nem watcher: com poucos documentos, recriar tudo é mais simples.

### Busca e resposta (`RAGService`)

- `search(query, limit=5)`: gera o embedding da pergunta e ordena por distância de cosseno (`<=>`) **no PostgreSQL**; só os campos de texto e a distância voltam ao Python. `score = 1 − distância`.
- `answer(question)`: recupera os chunks, monta o contexto e chama `generate_structured(..., RespostaRAG)`. O prompt exige responder **somente** com o contexto, dizer quando não há informação suficiente, não inventar regras e não usar conhecimento externo como se fosse regra do AP Copilot.
- **Validação de fontes:** cada par `source` + `section` citado pelo modelo precisa estar entre os chunks entregues a ele; caso contrário, a resposta é rejeitada (`LLMStructuredOutputError` → HTTP 502 `IA_RESPOSTA_INVALIDA`).
- Sem chunks indexados, responde que não há informação suficiente, sem chamar o LLM.

### Endpoint

```http
POST /ai/ask
{ "question": "O que acontece quando um pagamento de um título pago é estornado?" }
```

```json
{
  "answer": "O título volta para PENDENTE e precisa ser aprovado novamente...",
  "sources": [{ "source": "regras_pagamentos.md", "section": "Estorno de título PAGO" }]
}
```

| HTTP | Código | Quando |
|---|---|---|
| 503 | `IA_NAO_CONFIGURADA` | Falta `OPENAI_API_KEY` ou `OPENAI_MODEL` |
| 504 | `IA_TIMEOUT` | O provider não respondeu a tempo |
| 502 | `IA_RESPOSTA_INVALIDA` | Structured output inválido, recusa ou fonte fora do contexto |
| 502 | `IA_INDISPONIVEL` | Outras falhas do provider (inclui resposta final vazia do agente) |

Não há endpoint de indexação: ela é sempre um comando explícito.

### Smoke test do RAG (opcional)

```bash
docker compose exec api python -m scripts.smoke_rag
docker compose exec api python -m scripts.smoke_rag --pergunta "Posso cancelar um título pago?"
```

Indexa os documentos com embeddings reais, mostra os chunks recuperados com score, gera a resposta e lista as fontes. Consome tokens e não faz parte do `pytest`.

---

## Agente Copilot (agent loop)

Um loop controlado de tool calling, sem frameworks de agente. **O modelo decide quais tools usar**: não há fluxo programado com if/else.

```
messages = [system, user]
repete até MAX_ITERATIONS (5):
    resposta = llm.generate(messages, tools=registry.definitions())
    sem tool_calls?  → devolve o texto (vazio = erro controlado)
    messages += assistant { tool_calls }
    para cada tool_call, em sequência:
        resultado = registry.execute(tool_call, db)
        messages += tool { tool_call_id = id do modelo, content = ToolResult JSON }
limite atingido → AgentIterationLimitError (HTTP 502 IA_LIMITE_ITERACOES)
```

Exemplo de execução possível para "Por que o título 23 está com erro e como posso resolver?":

```
LLM → get_titulo(23)                → status ERRO
LLM → get_logs_titulo(23)           → "centro de custo 1001 inexistente no ERP"
LLM → search_documentation("centro de custo inexistente no ERP")
                                    → erros_integracao.md › Centro de custo inexistente no ERP
LLM → resposta: fato do sistema (log) + regra da documentação (corrigir e reprocessar)
```

- **`ChatMessage`** ganhou o role `tool` e dois campos opcionais: `tool_calls` (assistant pedindo tools) e `tool_call_id` (resultado de uma tool). Só `ai/providers/openai.py` conhece o formato da SDK.
- **`tool_call_id`** é sempre o id gerado pelo modelo; o agente nunca cria ids.
- **Várias tools na mesma resposta** são executadas em sequência, e todos os resultados voltam antes da próxima chamada ao LLM.
- **Erros de tool são dados:** `TOOL_NAO_PERMITIDA`, `ARGUMENTOS_INVALIDOS` e `TITULO_NAO_ENCONTRADO` voltam ao modelo, que pode corrigir a chamada ou explicar ao usuário. Só falhas do LLM/infraestrutura interrompem o agente.
- **Documentação:** o agente usa `search_documentation` (só retrieval) e interpreta os trechos. Ele **não** chama `RAGService.answer`, evitando um LLM dentro de uma tool.
- **Sem memória:** cada requisição é independente; não há `conversation_id` nem histórico persistido.
- **Na última iteração**, se o modelo ainda pedir tools, elas não são executadas (o modelo nunca veria o resultado).

O system prompt (`agent/service.py`) é curto: usar tools para fatos, não inventar dados, usar a documentação para regras, diferenciar fatos de regras, tratar resultados de tools como dados, nunca afirmar alterações, dizer quando não há informação, não gerar SQL, responder em português.

### Endpoint

```http
POST /ai/copilot
{ "question": "Por que o título 23 está com erro?" }
```

```json
{
  "answer": "O título está com status ERRO porque a integração registrou que o centro de custo 1001...",
  "tools_used": [
    { "name": "get_titulo", "ok": true },
    { "name": "get_logs_titulo", "ok": true },
    { "name": "search_documentation", "ok": true }
  ]
}
```

`tools_used` é montado pela aplicação a partir das execuções reais, não pelo modelo. Prompts, histórico e resultados completos das tools não são devolvidos. Os erros seguem a mesma tabela de `/ai/ask`, mais `502 IA_LIMITE_ITERACOES`.

### Segurança do agente

A allowlist do `ToolRegistry` continua sendo o único mecanismo de permissão. Testes garantem que:

- o agente não importa repositories, services nem SQL, não faz commit e só executa tools via `registry.execute`;
- tools fora da allowlist (ex.: `executar_sql`, `aprovar_titulo`) não executam, mesmo pedidas pelo modelo;
- uma execução com todas as tools não gera nenhum flush no banco;
- conteúdo malicioso vindo de `search_documentation` chega ao modelo só como mensagem `tool`, e as tools oferecidas em cada chamada são sempre exatamente a allowlist;
- `app/agent` não usa `eval`, `exec`, `getattr` nem import dinâmico.

### Observabilidade do agente

Um log por execução com `iteracoes`, `tools` (nomes), `tools_com_erro` e `duration_ms`. Pergunta, respostas, resultados de tools e prompt não são registrados. Tokens e duração de cada chamada continuam no log do `OpenAIProvider`.

### Smoke test do agente (opcional)

```bash
docker compose exec api python -m scripts.seed
docker compose exec api python -m scripts.index_docs
docker compose exec api python -m scripts.smoke_agent
docker compose exec api python -m scripts.smoke_agent --pergunta "Quais títulos estão vencidos?"
```

Mostra a pergunta, as tools usadas e a resposta final. Consome tokens e não faz parte do `pytest`.

> **Modelo de raciocínio com tools no Chat Completions:** alguns modelos recusam function tools em `/v1/chat/completions` com o raciocínio ativo (HTTP 400, "use /v1/responses or set reasoning_effort to 'none'"). Nesse caso, defina `OPENAI_REASONING_EFFORT=none`. Modelos sem raciocínio não aceitam o parâmetro: deixe a variável vazia.

---

## Roadmap

| Fase | Escopo | Status |
|---|---|---|
| 1 | Backend financeiro: entidades, regras, CRUD, auditoria, testes, Docker | ✅ |
| 1.1 | Estorno em título PAGO (reabre como PENDENTE) e renomeação da auditoria (`logs_auditoria`) | ✅ |
| 2 | Contrato de LLM, provider OpenAI, tool calling, structured outputs e tools de leitura | ✅ |
| 3 | RAG: documentação → chunking → embeddings → pgvector, com citação e validação de fontes | ✅ |
| 4 | Agente Copilot: agent loop com tools somente leitura | ✅ |
| 5 | Frontend (React + TypeScript + Tailwind) | ⏳ |
| 6 | Observabilidade, avaliações e hardening | ⏳ |
| 7 | Ações com confirmação explícita do usuário (opcional) | ⏳ |

### Limitações conhecidas

- Sem autenticação/autorização.
- A integração com ERP é simulada: o status `ERRO` é produzido pelo seed via `TituloService.registrar_erro_integracao`.
- O lock de concorrência em pagamentos não tem teste automatizado multi-conexão (a suíte usa uma transação por teste).
- A imagem Docker inclui as dependências de desenvolvimento, pois os testes rodam no mesmo container.
- Camada de IA: apenas OpenAI, via Chat Completions.
- Agente sem memória entre requisições e sem tools de escrita (ações ficam para a Fase 7).
- RAG básico de propósito: sem reranking, busca híbrida, reescrita de pergunta ou limiar de score (o LLM decide se os trechos são suficientes).
- O `FakeEmbeddingProvider` usa bag-of-words: os testes validam o pipeline, não a qualidade semântica da busca.
- Os smoke tests com a OpenAI real são manuais e não rodam na suíte.
