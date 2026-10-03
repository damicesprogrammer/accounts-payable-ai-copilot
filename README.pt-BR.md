<p align="right">
  <strong>Português</strong> ·
  <a href="README.md">English</a>
</p>

# AP Copilot

> **AI Engineering aplicada a Contas a Pagar** — regras financeiras determinísticas, tool calling tipado, RAG com pgvector, um agent loop controlado e avaliações com o modelo real.

O AP Copilot é um projeto de portfólio que demonstra como um LLM pode operar sobre um domínio de negócio realista **sem acesso direto ao banco de dados, sem SQL arbitrário e sem ser responsável por cálculos financeiros**.

Ele não é, intencionalmente, um ERP completo. O domínio é pequeno o suficiente para ser entendido de ponta a ponta, mas ainda inclui regras financeiras realistas, auditabilidade, cenários de falha, retrieval, uso de tools, avaliação e uma separação clara entre o modelo, a camada de negócio e a camada de apresentação.

![AP Copilot demo](docs/assets/ap-copilot-demo.gif)

## Destaques

- **Backend financeiro determinístico** com regras de negócio explícitas, limites de transação, logs de auditoria e lock de linha.
- **Tool calling tipado** por meio de uma allowlist explícita — o LLM nunca recebe acesso arbitrário ao banco de dados.
- **Agent loop controlado** com iterações limitadas (`MAX_ITERATIONS = 5`) e erros de tool estruturados.
- **RAG com PostgreSQL + pgvector**, implementado sem framework de agentes/RAG para que cada etapa fique visível.
- **Cálculos financeiros feitos pelo backend** com `Decimal` / `NUMERIC(14,2)` — o modelo explica os valores em vez de calcular dinheiro.
- **Suíte de evals com o modelo real** (25 casos) cobrindo seleção de tools pelo agente, finanças, segurança, retrieval do RAG e regressões encontradas no uso manual — incluindo uma regressão de moeda em EN-US.
- **Interface e respostas do Copilot em EN-US / PT-BR**, enquanto argumentos de tools, códigos de status, códigos de erro e o BRL como moeda do domínio permanecem inalterados.
- **Superfície de IA somente leitura por design** — nenhuma tool de escrita financeira é exposta ao agente.

## Cenários de demonstração

O dataset do seed contém cenários determinísticos pensados para testes e demonstração.

| Pergunta | Comportamento esperado |
|---|---|
| `How many pending invoices do we have?` | Chama `get_titulos_por_status(status="PENDENTE")` |
| `Which invoices are overdue?` | Chama `get_titulos_vencidos()` e usa totais calculados pelo backend |
| `Why is invoice 4 in error and how can I fix it?` | Combina dados do título, logs de auditoria e regras documentadas |
| `How many active suppliers do we have?` | Chama `get_fornecedores(ativo=true)` |
| `Can I approve an invoice that is only 50% allocated?` | Usa `search_documentation` para a regra documentada |
| `How do I make lasagna?` | Recusa, porque a pergunta está fora do domínio do AP Copilot |

A interface mostra as **tools realmente executadas pela aplicação**. `tools_used` é montado a partir das execuções reais, não gerado pelo modelo.

---

## Arquitetura

```text
                                  ┌───────────────────┐
                                  │   React frontend  │
                                  │   EN-US / PT-BR   │
                                  └─────────┬─────────┘
                                            │
                                            ▼
┌──────────────┐      ┌─────────────────────────────────────────┐
│   OpenAI     │◄────►│                FastAPI                  │
│ chat + emb.  │      │                                         │
└──────────────┘      │  API routes                             │
                      │      │                                  │
                      │      ├────► AgentService                 │
                      │      │          │                        │
                      │      │          ▼                        │
                      │      │      ToolRegistry                 │
                      │      │          │                        │
                      │      │          ▼                        │
                      │      │        Tools                      │
                      │      │          │                        │
                      │      ├──────────┴────► Services          │
                      │      │                    │              │
                      │      │                    ▼              │
                      │      │               Repositories        │
                      └──────┼────────────────────┼──────────────┘
                             │                    │
                             │                    ▼
                             │           PostgreSQL + pgvector
                             │
                             └────► RAGService
                                      │
                                      └────► embeddings + vector search
```

### Fluxo de negócio

```text
HTTP
  ↓
Pydantic schemas
  ↓
Services            ← regras de negócio + limite de transação
  ↓
Repositories        ← apenas acesso a dados
  ↓
PostgreSQL
```

### Fluxo de tools de IA

```text
LLM
  ↓ solicita uma tool pelo nome
ToolRegistry         ← allowlist explícita
  ↓ valida os argumentos
Typed Tool
  ↓
Service
  ↓
Repository
  ↓
PostgreSQL
```

O LLM **não** recebe executor de SQL, repository, sessão de banco de dados, mecanismo de import dinâmico nem tool de consulta genérica.

---

## Principais decisões de design

### O backend calcula; o LLM explica

Os agregados financeiros são calculados pelo backend.

Por exemplo, `get_titulos_vencidos()` retorna valores determinísticos como:

- quantidade de títulos vencidos;
- valor total original;
- saldo pendente total;
- por título: valor total, valor pago e saldo restante.

`get_titulos_por_status(status)` e `get_fornecedores(ativo?)` também retornam uma `quantidade` calculada sobre todos os registros correspondentes, independente de qualquer limite de listagem.

O modelo apresenta esses valores em vez de recalculá-los.

Essa regra veio de uma falha real durante o desenvolvimento: o LLM identificou os títulos vencidos corretos, mas produziu um agregado incorreto. O cálculo passou definitivamente para o backend.

### Tools semânticas em vez de acesso genérico ao banco

O agente trabalha com tools orientadas ao domínio e somente leitura:

```text
get_titulo(titulo_id)
get_titulos_por_status(status)
get_titulos_vencidos()
get_fornecedores(ativo?)
get_rateios_titulo(titulo_id)
get_pagamentos_titulo(titulo_id)
get_logs_titulo(titulo_id)
search_documentation(query)
```

Isso evita os dois extremos:

```text
específico demais
✗ get_quantidade_fornecedores_ativos()
✗ get_quantidade_fornecedores_inativos()

poderoso demais
✗ execute_sql(...)
✗ query_database(...)

orientado ao domínio
✓ get_fornecedores(ativo?)
✓ get_titulos_por_status(status)
```

Os parâmetros são tipados: `status` precisa ser um valor do enum `StatusTitulo` e `ativo`, um booleano. Não há filtros livres, nomes de coluna nem operadores.

### O comportamento do prompt não é a fronteira de segurança

O system prompt diz ao Copilot como se comportar, mas as permissões são garantidas pela arquitetura da aplicação.

Mesmo que o modelo solicite uma tool inexistente, o registry a rejeita. Os argumentos das tools são validados pelo Pydantic antes da execução.

---

## Domínio financeiro

O projeto modela um fluxo simplificado de Contas a Pagar com:

- fornecedores;
- centros de custo;
- títulos a pagar;
- rateios;
- pagamentos;
- estornos de pagamento;
- erros de integração;
- logs de auditoria.

### Ciclo de vida do título

```text
PENDENTE ──aprovar──► APROVADO ──(pagamentos confirmados = total)──► PAGO
 ▲ │  ▲                  │                                             │
 │ │  └──reprocessar── ERRO ◄── falha de integração                    │
 │ └──────cancelar───────┴──► CANCELADO                                │
 └───────────────────────── estorno de pagamento ──────────────────────┘
```

- `ERRO` pode ser alcançado a partir de `PENDENTE` ou `APROVADO`; o reprocessamento o leva de volta a `PENDENTE`.
- `PENDENTE`, `APROVADO` e `ERRO` podem ser cancelados; `CANCELADO` é final.
- Um pagamento estornado em um título `PAGO` faz o título voltar a `PENDENTE`, então ele precisa ser aprovado de novo antes de receber novos pagamentos.

### Regras de negócio selecionadas

- Rateios não podem exceder o valor do título.
- A aprovação exige exatamente 100% de rateio.
- Pagamentos só são aceitos para títulos `APROVADO`.
- Pagamentos não podem exceder o saldo pendente.
- Um título passa a `PAGO` automaticamente quando os pagamentos confirmados igualam exatamente o seu total.
- Um fornecedor inativo não pode receber um novo título.
- Um centro de custo inativo não pode receber um novo rateio.
- Um título com pagamentos confirmados não pode ser cancelado.
- Um título reaberto não pode ter o valor reduzido abaixo do valor já pago.
- Alterações relevantes são gravadas na trilha de auditoria na mesma transação da operação de negócio.

Valores monetários usam `NUMERIC(14,2)` no PostgreSQL e `Decimal` no Python — nunca ponto flutuante binário.

Mutações de título carregam a linha com `SELECT ... FOR UPDATE` para proteger os saldos contra alterações concorrentes.

---

## Camada de IA

### Contratos de provider

Os detalhes do SDK da OpenAI ficam dentro das implementações de provider (Chat Completions para geração, embeddings para retrieval).

```text
LLMProvider
├── OpenAIProvider
└── FakeLLMProvider       ← testes determinísticos

EmbeddingProvider
├── OpenAIEmbeddingProvider
└── FakeEmbeddingProvider ← testes determinísticos
```

A API financeira pode iniciar sem uma API key da OpenAI. Erros de configuração só ocorrem quando uma operação que depende de IA é chamada.

### Agent loop controlado

```text
messages = [system, user]

repeat up to MAX_ITERATIONS (5):
    call LLM with current messages + tool definitions

    if there are no tool calls:
        return final answer

    execute requested tools through ToolRegistry
    append tool results
    continue

iteration limit reached:
    controlled error
```

Falhas de tool, como argumentos inválidos ou recursos inexistentes, voltam ao modelo como dados estruturados para que ele possa corrigir a chamada ou explicar o problema.

Cada requisição é independente; não há memória de conversa persistente.

### Escopo

O Copilot **não** é, intencionalmente, um assistente de uso geral.

```text
pergunta sobre dados do sistema
→ tool operacional

pergunta sobre regra de negócio
→ search_documentation

dentro do domínio, mas não documentado
→ explica que a informação não está disponível

fora do domínio
→ recusa curta
```

### Idioma

`POST /ai/copilot` aceita `language` (`pt-BR` ou `en-US`, padrão `pt-BR`), e a resposta acompanha esse idioma. Só a regra de idioma do system prompt muda entre os locales.

Os rótulos voltados ao usuário são localizados; os valores de domínio voltados à máquina permanecem estáveis:

```text
backend / API / argumento de tool:  PENDENTE   APROVADO   PAGO   CANCELADO   ERRO
rótulo pt-BR:                        Pendente   Aprovado   Pago   Cancelado   Erro
rótulo en-US:                        Pending    Approved   Paid   Canceled    Error
```

Em EN-US, o Copilot escreve "pending" ou "approved" na resposta, mas as chamadas de tools continuam usando `PENDENTE` / `APROVADO`. Nomes de tools, códigos de erro, valores do banco de dados e o BRL (`R$`) como moeda do domínio nunca são traduzidos.

---

## RAG

O pipeline de RAG é implementado diretamente, sem framework.

```text
documentos Markdown
    ↓
chunking por heading
    ↓
embeddings da OpenAI (1536 dimensões)
    ↓
PostgreSQL / pgvector
    ↓ busca por distância de cosseno
top 5 chunks
    ↓
resposta estruturada do LLM
    ↓
validação das fontes
```

A base de conhecimento contém pequenos documentos fictícios alinhados com as regras implementadas no código.

O retrieval usa diretamente a distância vetorial do PostgreSQL:

```sql
ORDER BY embedding <=> :query_embedding
LIMIT 5
```

Na escala atual, intencionalmente não há índice HNSW/IVFFlat, reranker, busca híbrida nem reescrita de consulta. A busca vetorial exata sobre algumas dezenas de chunks é mais simples e determinística o suficiente para este projeto.

Em `/ai/ask`, todo `(source, section)` citado pelo modelo precisa ter estado presente no contexto recuperado; caso contrário, a resposta é rejeitada. Dentro do agente, `search_documentation` só faz o retrieval e devolve os chunks ao modelo como dados.

---

## Avaliações de IA

O repositório inclui um eval runner leve que usa o **modelo real da OpenAI**. Ele é separado do `pytest`, consome tokens e não faz parte da suíte de testes determinística normal.

```bash
docker compose exec api python -m evals.runner
docker compose exec api python -m evals.runner --category safety
docker compose exec api python -m evals.runner --case agent_titulo_erro
```

### O que os evals medem

| Categoria | Casos | Exemplos |
|---|---|---|
| `agent` | 8 | seleção de tools para situação do título, erros de integração, filtros de status e fornecedores |
| `finance` | 4 | totais calculados pelo backend, saldos pendentes e preservação do BRL em EN-US |
| `safety` | 8 | recusa fora do domínio, capacidades não documentadas e prompt injection (na pergunta e dentro de texto recuperado) |
| `rag` | 5 | source/section esperados nos chunks recuperados, com o score de retrieval registrado |

Os números esperados são resolvidos pelos services antes de cada execução, não ficam fixos nos casos.

Os checks focam em invariantes, não no texto exato:

- tools obrigatórias;
- tools proibidas;
- conteúdo esperado / proibido;
- limites de tamanho da resposta;
- chunks de retrieval esperados;
- nenhuma escrita inesperada no banco de dados;
- nenhuma tool fora da allowlist;
- idioma da requisição (`language`);
- moeda somente BRL (`brl_only`: exige `R$`, rejeita `$` fora de `R$` e `USD`).

A última execução com o modelo real passou **25/25**.

### Os evals evoluem a partir de falhas reais

Uma suíte verde só prova os cenários que ela cobre atualmente.

Uma execução anterior totalmente verde (20/20) ainda deixava passar este comportamento:

```text
"Quantos títulos pendentes temos?"
```

O agente usou `get_titulos_vencidos()` porque nenhuma tool expunha filtro por status de título. `PENDENTE` é um status do workflow; `VENCIDO` depende da data.

A correção foi:

```text
falha manual
→ identificar a capacidade ausente
→ adicionar get_titulos_por_status(status)
→ adicionar evals de regressão permanentes
```

Uma regressão parecida aconteceu depois de adicionar EN-US: o modelo exibiu valores em BRL com `$`. A regra de idioma agora mantém `R$`, e o eval `finance_vencidos_en_us_preserva_brl` verifica isso com `brl_only`.

Esse ciclo de feedback é intencional:

```text
uso real
→ falha
→ investigação
→ correção mínima
→ eval permanente
```

---

## Frontend

O frontend em React é intencionalmente pequeno e somente leitura.

Ele demonstra:

- lista de Contas a Pagar com filtros aplicados pelo backend;
- detalhes do título;
- rateios;
- pagamentos confirmados e estornados;
- trilha de auditoria;
- respostas do AI Copilot renderizadas como Markdown (HTML bruto não é renderizado);
- tools realmente executadas pelo Copilot;
- seletor de idioma EN-US / PT-BR persistido no `localStorage`;
- rótulos localizados de status e de tipo de auditoria voltados ao usuário.

O navegador nunca se comunica diretamente com a OpenAI. A `OPENAI_API_KEY` fica no servidor da API.

Os cálculos financeiros continuam no backend; o frontend apenas apresenta e localiza. Valores são exibidos em BRL e datas como `dd/mm/yyyy` nos dois idiomas. Textos gravados pelo backend, como as mensagens dos logs de auditoria, são exibidos como foram registrados.

---

## Stack

| Camada | Tecnologias |
|---|---|
| API | Python 3.12, FastAPI, Pydantic v2 |
| Persistência | PostgreSQL 16, pgvector, SQLAlchemy 2.0, Alembic |
| IA | OpenAI SDK atrás de contratos próprios, structured outputs, embeddings, tool calling |
| Frontend | React, TypeScript, Vite, Tailwind CSS, React Router |
| Testes | pytest, Vitest, Testing Library |
| Qualidade | Ruff, ESLint |
| Infraestrutura | Docker, Docker Compose, uv |

---

## Início rápido

### Requisitos

- Docker com Docker Compose
- API key da OpenAI apenas para embeddings, chamadas reais ao Copilot, smoke tests e evals
- Node.js 22+ apenas se for rodar o frontend fora do Docker

### 1. Configure o ambiente

```bash
cp .env.example .env
```

Para usar os recursos de IA, defina `OPENAI_API_KEY`, `OPENAI_MODEL` e `OPENAI_EMBEDDING_MODEL` no `.env`.

O arquivo `.env` não é versionado.

### 2. Suba a stack

```bash
docker compose up -d --build
```

Isso sobe o PostgreSQL, a API e o frontend. As migrations rodam quando o container da API inicia.

### 3. Popule o banco de dados

```bash
docker compose exec api python -m scripts.seed
docker compose exec api python -m scripts.seed --reset   # wipe and recreate
```

O seed cria fornecedores, centros de custo e títulos fictícios por meio dos próprios services, incluindo cenários de títulos vencidos, parcialmente rateados, parcialmente pagos, com erro de integração, cancelados e totalmente pagos.

### 4. Indexe a base de conhecimento

```bash
docker compose exec api python -m scripts.index_docs
```

Esta etapa exige um modelo de embeddings da OpenAI configurado.

### 5. Abra a aplicação

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`

Smoke tests opcionais com o modelo real: `scripts.smoke_openai`, `scripts.smoke_rag` e `scripts.smoke_agent` (rode com `docker compose exec api python -m ...`).

### Desenvolvimento do frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Testes e qualidade

### Backend

```bash
docker compose exec api pytest
docker compose exec api ruff check .
```

300+ testes de backend. Eles rodam contra o PostgreSQL, sem substituí-lo por SQLite.

A suíte cobre:

- regras de negócio;
- fluxos HTTP;
- contratos de provider;
- tool registry e validação de argumentos;
- chunking, indexação e retrieval do RAG;
- comportamento do agent loop;
- invariantes de segurança;
- comportamento do eval runner.

Execuções normais do `pytest` usam providers fake e não chamam a API real da OpenAI.

### Frontend

```bash
cd frontend
npm test
npm run lint
npm run build
```

30+ testes de frontend, cobrindo a página do Copilot, o layout e o seletor de idioma, os rótulos de status localizados e o comportamento do cliente da API. As regras de negócio financeiras não são duplicadas nos testes de frontend.

---

## Visão geral da API

| Método | Rota | Finalidade |
|---|---|---|
| `GET/POST` | `/fornecedores` | listar / criar fornecedores |
| `GET/PUT` | `/fornecedores/{id}` | consultar / atualizar fornecedor |
| `GET/POST` | `/centros-custo` | listar / criar centros de custo |
| `GET/PUT` | `/centros-custo/{id}` | consultar / atualizar centro de custo |
| `GET/POST` | `/titulos` | listar / criar títulos |
| `GET/PUT` | `/titulos/{id}` | detalhe / atualização do título |
| `POST` | `/titulos/{id}/aprovar` | aprovar título |
| `POST` | `/titulos/{id}/cancelar` | cancelar título |
| `POST` | `/titulos/{id}/reprocessar` | levar `ERRO` de volta a `PENDENTE` |
| `GET/POST` | `/titulos/{id}/rateios` | listar / criar rateios |
| `DELETE` | `/titulos/{id}/rateios/{rateio_id}` | remover rateio |
| `GET/POST` | `/titulos/{id}/pagamentos` | listar / registrar pagamentos |
| `POST` | `/titulos/{id}/pagamentos/{pagamento_id}/estornar` | estornar pagamento |
| `GET` | `/titulos/{id}/logs` | trilha de auditoria |
| `POST` | `/ai/ask` | resposta RAG com fontes validadas |
| `POST` | `/ai/copilot` | Copilot agêntico somente leitura |
| `GET` | `/health` | health check |

O OpenAPI contém os contratos completos de requisição/resposta.

---

## Observabilidade

A aplicação registra metadados estruturados em vez do conteúdo dos prompts.

Chamadas ao LLM:

```text
provider, model, duration_ms, input_tokens, output_tokens, finish_reason, tool_calls
```

Execuções do agente:

```text
iteracoes, tools, tools_com_erro, input_tokens, output_tokens, duration_ms
```

Execuções de tools (`tool`, `ok`, `error_code`, `duration_ms`) e chamadas de embeddings (`model`, `textos`, `input_tokens`, `duration_ms`) são registradas da mesma forma.

Prompts, perguntas dos usuários, respostas completas e documentos recuperados na íntegra não são gravados intencionalmente nos logs da aplicação.

---

## Modelo de segurança

O projeto separa o **comportamento do modelo** das **permissões da aplicação**.

- As tools são registradas por meio de uma allowlist explícita.
- Os argumentos das tools usam Pydantic com `extra="forbid"`.
- O agente não tem tool de SQL.
- O agente não pode escolher dinamicamente repositories ou código da aplicação.
- As tools chamam services, não repositories.
- As tools do agente são somente leitura.
- Resultados de tools são tratados como dados, inclusive texto recuperado contendo instruções maliciosas.
- Tools inesperadas são rejeitadas antes da execução.
- Erros internos não são expostos ao cliente.
- Timeouts e falhas do provider de IA são mapeados para erros estáveis da API.
- O navegador nunca recebe a API key da OpenAI.

Essas medidas reduzem riscos; não são uma alegação de segurança completa.

---

## Estrutura do projeto

```text
backend/
├── app/
│   ├── agent/          # agent loop controlado do Copilot
│   ├── ai/             # contratos e providers de LLM / embeddings
│   ├── api/            # rotas FastAPI
│   ├── core/           # configuração, sessão do banco, erros, logging
│   ├── models/         # entidades SQLAlchemy
│   ├── rag/            # chunking, retrieval vetorial, serviço de RAG
│   ├── repositories/   # acesso a dados
│   ├── schemas/        # contratos da API
│   ├── services/       # regras de negócio e limites de transação
│   └── tools/          # tools explícitas e somente leitura do agente
├── docs/               # base de conhecimento fictícia do AP Copilot
├── evals/              # casos e runner de avaliação com o modelo real
├── scripts/            # seed, indexação, smoke tests
└── tests/

frontend/
└── src/
    ├── api/            # cliente da API
    ├── components/
    ├── pages/
    ├── types/
    ├── utils/          # formatação
    └── i18n.ts         # textos EN-US / PT-BR e rótulos do domínio
                        # (os testes ficam ao lado do código: *.test.ts / *.test.tsx)

docs/assets/            # GIF de demonstração do README
```

---

## Limitações conhecidas

Este é um projeto de portfólio, não um ERP de produção.

- Sem autenticação nem autorização.
- O frontend é somente leitura.
- A lista de títulos não tem paginação na interface e exibe até 200 registros.
- Falhas de integração com o ERP são simuladas por cenários do seed.
- O lock de linha está implementado, mas não há teste automatizado de concorrência com múltiplas conexões.
- As imagens Docker incluem dependências de desenvolvimento, e o frontend roda no servidor de desenvolvimento do Vite.
- A camada de IA suporta atualmente apenas a OpenAI.
- O Copilot não tem memória de conversa persistente.
- Não há tools de escrita para o agente.
- O RAG intencionalmente não tem reranking, busca híbrida, reescrita de consulta nem limiar de score.
- Valores e datas usam formatação brasileira nos dois idiomas da interface.
- Smoke tests e evals com o modelo real são executados manualmente; não há pipeline de CI.
- Os checks dos evals medem invariantes definidos; não são uma medida geral de qualidade linguística. Apenas um caso de eval roda em EN-US.

---

## Roadmap

### Concluído

- [x] Backend financeiro, regras, auditoria e Docker
- [x] Abstração de provider de LLM, structured outputs e tool calling tipado
- [x] RAG com embeddings e pgvector
- [x] Agent loop controlado
- [x] Frontend em React
- [x] Observabilidade de IA, evals com o modelo real e hardening
- [x] Interface e respostas do Copilot em EN-US / PT-BR
- [x] Rótulos de status localizados para o usuário

### Próximo passo opcional

- [ ] Ações de escrita com **confirmação explícita do usuário** antes de qualquer mutação financeira

O Copilot atual continua somente leitura por design.

---

## Princípios de design

```text
LLM
  interpreta
  seleciona tools
  explica

Backend
  calcula
  valida
  aplica as regras de negócio
  controla as transações

Frontend
  apresenta
  localiza
```

Essa fronteira é a ideia central do projeto.
