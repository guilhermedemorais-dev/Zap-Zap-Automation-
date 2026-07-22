# TASK-001: Implementar runtime LangGraph da Lara

> Task é ordem de execução. Aponta para specs, issue, branch e PR.

## Status
Em revisão

## Tipo
Feature

## Prioridade
Alta

## Issue GitHub
criar issue: Implementar runtime LangGraph da Lara

## Branch sugerida
`feat/lara-langgraph-runtime`

## PR
Abrir PR após primeiro checkpoint validado localmente.

## Responsável
Executor: Codex/dev-implementation-standard. Revisor: Guilherme/dev-workflow-standard.

## Objetivo da task
Criar um runtime LangGraph para controlar estado e decisão da Lara, com contrato HTTP para o n8n e testes de jornada, sem publicar no remoto até existir URL estável e fallback.

## Contexto
O atendimento da Lara apresentou gargalo no n8n/prompt livre: saudação virando nome, repetição de abertura, mistura de contexto, agendamento incompleto e endereço errado. Pesquisa no repositório oficial `langchain-ai/langgraph`, commit `5931a5f`, confirmou o uso de `StateGraph`, `START`, `END`, `add_conditional_edges`, `compile(checkpointer=...)` e `thread_id` via `configurable` para memória por conversa.

## Specs obrigatórias
- `docs/specs/lara-langgraph/module-spec.md`
- `docs/specs/lara-langgraph/api.md`

## Docs obrigatórios
- `docs/LARA_MASTER_EXECUTION_PLAN.md`
- `docs/LARA_REFERENCE_REPOS_AUDIT.md`
- `docs/LARA_LANGGRAPH_RUNTIME.md`
- `docs/ORION_WF_BOT_V7_CURRENT_FLOW.md`

## Escopo
- Criar módulo `lara_langgraph`.
- Criar serviço FastAPI.
- Criar requirements e Dockerfile.
- Implementar grafo com checkpointer por `session_id`.
- Criar testes unitários de jornada.
- Criar smoke HTTP local.
- Documentar integração n8n.

## Fora do escopo
- Publicar no n8n remoto.
- Alterar workflow de produção sem URL e fallback.
- Criar catálogo online.
- Implementar deploy definitivo.
- Alterar CRM.

## Arquivos prováveis
- `lara_langgraph/`
- `tests/test_lara_langgraph.py`
- `requirements-langgraph.txt`
- `Dockerfile.langgraph`
- `scripts/lara_langgraph_smoke.py`
- `docs/LARA_LANGGRAPH_RUNTIME.md`
- `docs/specs/lara-langgraph/`

## Banco
Sem migração nesta task. Usar `InMemorySaver` para local. Produção exige decisão futura de checkpointer durável.

## API/Backend
Criar:

- `GET /health`
- `POST /v1/lara/turn`

## Frontend/UI
N/A.

## Regras de negócio
- Saudação não vira nome.
- Nome de perfil não vira nome confirmado.
- Agendamento exige motivo.
- Appointment exige confirmação.
- Endereço correto obrigatório.
- Não inventar link de produto.
- Memória isolada por `session_id`.

## Critérios de aceite
- `python -m unittest tests/test_lara_langgraph.py` passa.
- Serviço sobe com Uvicorn.
- `/health` retorna 200.
- Smoke HTTP executa saudação, nome e intenção de agendamento.
- Mesma `session_id` preserva estado via LangGraph checkpointer.
- Documentação informa bloqueio de produção sem URL/fallback.

## TDD / Testes obrigatórios
- Testes de saudação curta.
- Testes de nome após saudação.
- Testes para bloquear saudação como nome.
- Testes de erro de digitação em agendamento.
- Testes de slots.
- Testes de motivo antes de appointment.
- Testes de confirmação.
- Teste de memória por `session_id` sem `state` manual.

## Segurança
- Não adicionar segredos.
- Não logar tokens.
- Não expor endpoint em produção sem autenticação ou rede privada.

## Observabilidade/logs
- Health check.
- Futuro: log estruturado por `session_id`, `intent`, `stage`, `next_action`.

## Instrução para IA/dev
Use esta task como contrato operacional. Leia as specs obrigatórias antes de codar. Ajuste a implementação já iniciada para ficar aderente ao LangGraph oficial, especialmente `START`, `compile(checkpointer=...)` e `thread_id`. Não altere o n8n remoto nesta task.

## Resultado da execução

### Resumo
Runtime LangGraph criado com API FastAPI, grafo de estados, checkpointer por `session_id`, testes de jornada e smoke HTTP local. Integração remota com n8n ainda não foi publicada porque falta URL estável do serviço e fallback.

### Arquivos alterados
- `lara_langgraph/__init__.py`
- `lara_langgraph/graph.py`
- `lara_langgraph/service.py`
- `tests/test_lara_langgraph.py`
- `requirements-langgraph.txt`
- `Dockerfile.langgraph`
- `scripts/lara_langgraph_smoke.py`
- `docs/LARA_LANGGRAPH_RUNTIME.md`
- `docs/specs/lara-langgraph/module-spec.md`
- `docs/specs/lara-langgraph/api.md`
- `docs/tasks/TASK-001-lara-langgraph-runtime.md`
- `docs/LARA_MASTER_EXECUTION_PLAN.md`

### Comandos executados
- `git clone --depth 1 https://github.com/langchain-ai/langgraph.git /tmp/langgraph-official`
- `python3 -m venv /tmp/lara-langgraph-venv`
- `/tmp/lara-langgraph-venv/bin/pip install -r requirements-langgraph.txt`
- `/tmp/lara-langgraph-venv/bin/python -m unittest tests/test_lara_langgraph.py`
- `/tmp/lara-langgraph-venv/bin/uvicorn lara_langgraph.service:app --host 127.0.0.1 --port 8087`
- `curl -sS http://127.0.0.1:8087/health`
- `/tmp/lara-langgraph-venv/bin/python scripts/lara_langgraph_smoke.py http://127.0.0.1:8087`

### Resultado dos testes
- Unit: 9 testes passaram.
- Health HTTP: `{"status":"ok"}`.
- Smoke HTTP: saudação `Boa noite`, nome `Jhonatan` e intenção `qro agenda uma vizta` passaram mantendo `confirmed_name` por sessão.

### Bloqueios
Produção depende de URL estável do serviço e decisão de checkpointer durável.

### Observações
Context7 falhou por token OAuth expirado. grep.app falhou por rate limit. Fonte oficial usada: clone local de `https://github.com/langchain-ai/langgraph.git`, commit `5931a5f`.
