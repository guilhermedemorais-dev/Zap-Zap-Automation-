# SPEC: API/Backend - Lara V9 Shadow Workflow Contract

> Spec e contrato do que deve ser construido. Nao e PR, nao e task.

## Status
Em revisao

## Objetivo
Definir o contrato backend/workflow da Lara V9 para separar entrada, estado, supervisor, agentes, ferramentas, validador e saida, garantindo que QA/shadow rode sem side effects antes de qualquer publicacao em producao.

## Contexto
Specs relacionadas:

- `docs/specs/lara-v9/module-spec.md`
- `docs/specs/lara-v9/validation-rules.md`
- `docs/LARA_REFERENCE_BENCHMARK_20260709.md`
- `docs/ORION_WF_BOT_V7_CURRENT_FLOW.md`

## Endpoints

### Endpoint conceitual ou subworkflow: `POST /v9/turn`

- **Descricao:** processa uma mensagem da Lara V9 e retorna contrato estruturado.
- **Autenticacao/Autorizacao:** chamada interna do n8n ou servico protegido. Em producao, exigir segredo/header ou rede privada.
- **Parametros:** N/A.
- **Request body:**

```json
{
  "conversation_id": "whatsapp:+5547999999999",
  "whatsapp_number": "+5547999999999",
  "profile_name": "Nome do perfil, nao confiavel",
  "message": "Mensagem original do cliente",
  "message_type": "text|audio|image|document|unknown",
  "timestamp": "2026-07-09T16:47:00-03:00",
  "qa_mode": true,
  "source": "whatsapp|qa|root",
  "root_session_active": false,
  "state": {
    "stage": "inicio",
    "confirmed_name": null,
    "last_intent": null,
    "last_agent": null,
    "last_offered_slots": [],
    "pending_booking": null,
    "collected_context": {}
  }
}
```

- **Response:**

```json
{
  "ok": true,
  "conversation_id": "whatsapp:+5547999999999",
  "state_before": {
    "stage": "identificacao"
  },
  "state_after": {
    "stage": "descoberta",
    "confirmed_name": "Guilherme"
  },
  "agent": "agent_identity",
  "intent": "identification",
  "next_action": "reply",
  "reply_blocks": [
    "Perfeito, Guilherme.",
    "Me conta o que voce esta buscando hoje?"
  ],
  "tool_request": null,
  "crm_context": {
    "interest": "",
    "occasion": "",
    "appointment_reason": "",
    "summary_for_human": ""
  },
  "validation": {
    "passed": true,
    "blocked_reason": null
  },
  "side_effects": {
    "send_whatsapp": false,
    "create_appointment": false,
    "update_crm": false
  }
}
```

- **Codigos de status:** se for HTTP real:
  - 200: processado.
  - 400: payload invalido.
  - 401/403: chamada nao autorizada.
  - 422: contrato gerado violou regra P0.
  - 500: erro interno.

### Tool interna: `check_availability`

- **Descricao:** consulta horarios reais no CRM.
- **Autenticacao/Autorizacao:** credencial interna do n8n/CRM.
- **Request body:**

```json
{
  "conversation_id": "whatsapp:+5547999999999",
  "preferred_date": "2026-07-10",
  "period": "manha|tarde|qualquer",
  "qa_mode": true
}
```

- **Response:**

```json
{
  "ok": true,
  "slots": [
    {
      "starts_at": "2026-07-10T09:00:00-03:00",
      "ends_at": "2026-07-10T10:00:00-03:00",
      "label": "10/07 as 09:00"
    }
  ],
  "source": "crm|qa_mock"
}
```

### Tool interna: `create_appointment`

- **Descricao:** cria appointment real somente fora de QA e apos validacao P0.
- **Request body:**

```json
{
  "conversation_id": "whatsapp:+5547999999999",
  "customer_name": "Guilherme de Morais",
  "whatsapp_number": "+5547999999999",
  "phone_confirmed": true,
  "email": "cliente@email.com",
  "starts_at": "2026-07-10T09:00:00-03:00",
  "ends_at": "2026-07-10T10:00:00-03:00",
  "visit_reason": "Ver aliancas de casamento com gravacao interna",
  "crm_note": "Cliente busca aliancas de casamento prontas com gravacao interna. Quer atendimento presencial.",
  "qa_mode": false
}
```

- **Response:**

```json
{
  "ok": true,
  "appointment_id": "crm_appointment_id",
  "created": true,
  "source": "crm"
}
```

## Contratos e tipos

### `ConversationState`

```json
{
  "stage": "inicio|identificacao|descoberta|catalogo_info|agenda_slots|agenda_contexto|agenda_confirmacao|agenda_confirmado|handoff|encerrado",
  "confirmed_name": "string|null",
  "whatsapp_number": "string",
  "last_intent": "string|null",
  "last_agent": "string|null",
  "last_bot_action": "string|null",
  "last_offered_slots": [],
  "pending_booking": {},
  "collected_context": {
    "interest": null,
    "occasion": null,
    "appointment_reason": null,
    "deadline": null,
    "product_type": null,
    "personalization": null,
    "catalog_link_sent": false
  }
}
```

### `LaraContract`

```json
{
  "type": "reply|tool|handoff|root_admin|blocked",
  "agent": "agent_identity|agent_discovery|agent_catalog_info|agent_appointment|agent_handoff|root_admin",
  "intent": "string",
  "next_action": "reply|check_availability|create_appointment|update_lead|handoff|wait|none",
  "reply_blocks": [],
  "tool_request": {},
  "crm_context": {},
  "state_patch": {},
  "validation": {
    "passed": true,
    "blocked_reason": null
  }
}
```

## Regras de negocio aplicadas
Todas as regras de `docs/specs/lara-v9/validation-rules.md`.

## Banco
Sem migracao definida nesta spec.

Leituras/gravas previstas:

- estado por `conversation_id`;
- historico resumido;
- audit log ROOT;
- logs de validacao;
- contexto CRM.

## Integracoes externas
- n8n.
- UAZAPI/WhatsApp.
- CRM/agenda Orion/ORIN.
- possivel Postgres do CRM.
- JSONL/RAG local ou fonte futura do catalogo.

## Seguranca
- `qa_mode=true` deve bloquear side effects.
- endpoint interno deve exigir autenticacao.
- LLM output nunca chama ferramenta diretamente sem validacao.
- tokens nunca entram no payload visivel.

## Observabilidade/logs
Logar transicoes e bloqueios:

- `state_before`
- `state_after`
- `agent`
- `intent`
- `next_action`
- `validation.blocked_reason`
- `qa_mode`

## Testes
- contrato aceita payload valido;
- rejeita payload sem numero;
- rejeita comando ROOT desconhecido;
- bloqueia reset sem confirmacao;
- bloqueia appointment sem motivo;
- bloqueia side effects em QA;
- retorna `Perfeito, Guilherme` para `Meu nome e Guilherme`.

## Performance
- alvo: resposta de decisao em ate 3s antes dos delays humanizados;
- buscar agenda pode exceder isso, mas deve enviar pre-message controlada.

## Riscos
- n8n com muitos Code nodes pode ficar dificil de manter.
- runtime externo LangGraph exige deploy e monitoramento.
- banco de estado mal escolhido vira nova fonte de bug.

## Decisoes pendentes
1. Implementar `POST /v9/turn` como subworkflow n8n ou servico externo LangGraph?
2. Qual autenticacao interna usar?
3. Qual banco oficial do estado?
4. Quais campos exatos do CRM receberao `crm_context`?

## Criterios de aceite
- contrato JSON unico documentado e usado por todos os agentes/blocos;
- QA/shadow usa o mesmo contrato da producao;
- side effects bloqueados em QA;
- validacao P0 ocorre antes de WhatsApp/CRM;
- erros de contrato retornam motivo claro e auditavel.
