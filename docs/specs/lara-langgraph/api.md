# SPEC: API/Backend - Lara LangGraph Runtime

## Status
Em revisão

## Objetivo
Expor o grafo conversacional da Lara para o n8n por HTTP, mantendo estado por `session_id`/`thread_id` e retornando um contrato JSON que o n8n consiga transformar em resposta, busca de agenda ou criação de agendamento.

## Contexto
Módulo: `docs/specs/lara-langgraph/module-spec.md`

Referências:

- `docs/LARA_LANGGRAPH_RUNTIME.md`
- `docs/LARA_REFERENCE_REPOS_AUDIT.md`
- Repositório oficial LangGraph `langchain-ai/langgraph`, commit `5931a5f`
- Exemplo oficial usa `StateGraph`, `START`, `END`, `add_conditional_edges` e `compile`
- Implementação oficial documenta `compile(checkpointer=...)` e invocação com `config = {"configurable": {"thread_id": "..."}}`

## Endpoints

### `GET /health`

- **Descrição:** verifica se o serviço está vivo.
- **Autenticação/Autorização:** N/A na versão local. Produção deve restringir por rede ou token.
- **Response 200:**

```json
{"status":"ok"}
```

### `POST /v1/lara/turn`

- **Descrição:** processa uma mensagem do cliente e retorna decisão estruturada.
- **Autenticação/Autorização:** N/A local. Produção deve exigir token/header interno ou rede privada.
- **Request body:**

```json
{
  "session_id": "wa:+5547999990000",
  "phone": "+5547999990000",
  "profile_name": "Nome de perfil opcional",
  "message": "Boa noite",
  "state": {},
  "available_slots": []
}
```

Campos:

- `session_id`: obrigatório. Vira `thread_id` do LangGraph.
- `phone`: obrigatório em produção.
- `profile_name`: opcional, nunca vira nome confirmado sozinho.
- `message`: obrigatório.
- `state`: opcional. Compatibilidade com n8n atual. Não deve ser a fonte principal de memória em produção.
- `available_slots`: opcional. Usado quando o n8n já buscou horários no CRM.

Response 200:

```json
{
  "reply_blocks": [
    "Olá, boa noite. Tudo bem?",
    "Aqui é a Lara, consultora virtual da ORIN Joias.",
    "Para que eu consiga te oferecer um atendimento mais preciso, você poderia me informar seu nome?"
  ],
  "intent": "identification",
  "conversation_stage": "identificacao",
  "lead_temperature": "morno",
  "collected_context": {},
  "missing_fields": ["confirmed_name"],
  "next_action": "reply",
  "tool_payload": {},
  "crm_note": "",
  "state": {},
  "safety": {
    "used_confirmed_facts_only": true,
    "needs_human": false
  }
}
```

`next_action` permitido:

- `reply`: n8n envia `reply_blocks`.
- `check_availability`: n8n consulta CRM e chama o runtime novamente com `available_slots`.
- `create_appointment`: n8n cria appointment usando `tool_payload.appointment`.

Erros:

- 422: payload inválido do FastAPI/Pydantic.
- 500: erro interno sanitizado como `lara_langgraph_failed`.

## Contratos e tipos

Tipos principais:

- `session_id`: string.
- `reply_blocks`: array de strings, pronto para WhatsApp.
- `intent`: enum.
- `conversation_stage`: enum.
- `next_action`: enum.
- `tool_payload.appointment`: objeto com `name`, `phone`, `date`, `time`, `reason`, `interest`, `notes`.

## Regras de negócio aplicadas
Ver `docs/specs/lara-langgraph/module-spec.md`.

## Banco
Não cria tabela nesta task. A decisão de checkpointer persistente fica pendente. Primeira versão local usa `InMemorySaver`, produção deve usar persistência durável antes de liberar atendimento real.

## Integrações externas
- n8n chama o serviço.
- n8n continua chamando CRM.
- Serviço não chama OpenAI nesta primeira fase determinística.

## Segurança
- Não aceitar `session_id` gerado por IA.
- Não expor sem autenticação em produção.
- Não retornar stack trace.
- Não logar segredos.

## Observabilidade/logs
- Log mínimo por requisição: `session_id`, `conversation_stage`, `intent`, `next_action`.
- Health check obrigatório.

## Testes
- `python -m unittest tests/test_lara_langgraph.py`
- Smoke HTTP com `scripts/lara_langgraph_smoke.py`

## Performance
- Resposta local deve ser subsegundo para fluxo determinístico.
- Chamada HTTP do n8n deve ter timeout curto e fallback para o fluxo anterior durante rollout.

## Riscos
- Sem checkpointer persistente, restart perde memória.
- Sem fallback no n8n, queda do runtime derruba atendimento.
- Sem autenticação, endpoint pode ser abusado.

## Decisões pendentes
1. Backend do checkpointer de produção.
2. URL pública/interna do serviço.
3. Header/token de autenticação entre n8n e runtime.

## Critérios de aceite
- Endpoint valida payload.
- Endpoint retorna contrato JSON estável.
- Memória por `session_id` funciona sem depender de `state` manual do n8n.
- Testes obrigatórios passam.
