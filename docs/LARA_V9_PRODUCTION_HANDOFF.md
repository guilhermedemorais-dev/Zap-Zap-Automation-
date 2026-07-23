# Lara V9 - Handoff De Producao

## Resumo executivo

A Lara V9 ja esta criada no n8n remoto e, na ultima verificacao, era a unica workflow ativa retornada pela API do n8n.

Ela ainda nao deve ser declarada 100% pronta porque falta o teste real do usuario no WhatsApp depois da ultima correcao de `/rclear` e confirmacao final.

## Estado atual

- Workflow antigo de referencia: `ORION-WF-Bot-v7-LARA-SDR`
- ID antigo: `7SucjAi8zU69sQuT`
- Workflow V9 atual: `LARA V9 Shadow SDR`
- ID V9: `7kXu17NYpsN8Yc65`
- LangGraph interno: `http://lara-langgraph:8080/v1/lara/turn`
- Health: `http://lara-langgraph:8080/health`
- Numero de producao do cliente: `+55 47 9696-3593`

## O que ja foi validado

- QA remoto do n8n contra output real do shadow: `22/22` cenarios passaram apos o patch de entrada e o guard de estado.
- Execucoes single-turn atuais: `4067` a `4088`.
- QA multi-turn remoto do n8n: `4/4` jornadas passaram apos o guard que impede pedir nome de novo ao solicitar agendamento.
- Execucoes multi-turn atuais: `4055` a `4066`.
- Caso real coberto: depois de `Boa noite` + `Guilherme` + `Gostaria de agendar um atendimento`, a Lara chama `check_availability` e nao reinicia saudacao nem pede nome novamente.
- QA de contrato de entrada WhatsApp/provedor: `4/4` payloads passaram.
- Execucoes contrato de entrada: `3982` a `3985`.
- Payloads validados: UAZAPI atual, Evolution/Baileys `messages.upsert`, `data.text` e payload achatado defensivo.
- QA sem side effects: nenhuma execucao de teste rodou envio WhatsApp real, CRM real, agenda real ou save real do ROOT.
- Health do LangGraph validado de dentro do container n8n.
- Correcao de `/rclear` validada por smoke remoto direto no LangGraph.
- Correcao de confirmacao final como `Sim e isso mesmo` validada por smoke remoto direto no LangGraph.

## O que ainda falta

Falta o usuario validar a ultima alteracao pelo WhatsApp real.

Depois disso, executar o roteiro em:

- `docs/LARA_WHATSAPP_SHADOW_TEST_RUNBOOK.md`

Se o WhatsApp real repetir abertura, errar nome, inventar informacao, confirmar agenda antes do motivo ou mandar endereco errado, a V9 reprova e deve ser corrigida pela execution id mais recente.

## Como registrar a evidencia real

Exemplo com execution id:

```bash
python3 scripts/lara_record_whatsapp_evidence.py \
  --tester "Guilherme" \
  --test-number "+55 XX XXXXX-XXXX" \
  --execution-id "0000" \
  --notes "Teste WhatsApp shadow aprovado sem loop, sem nome errado e sem endereco errado." \
  --approve
```

Exemplo com print:

```bash
python3 scripts/lara_record_whatsapp_evidence.py \
  --tester "Guilherme" \
  --test-number "+55 XX XXXXX-XXXX" \
  --screenshot "/caminho/do/print.png" \
  --notes "Teste WhatsApp shadow aprovado." \
  --approve
```

Se falhar:

```bash
python3 scripts/lara_record_whatsapp_evidence.py \
  --tester "Guilherme" \
  --test-number "+55 XX XXXXX-XXXX" \
  --failure "Repetiu abertura depois do nome informado"
```

## Gate de producao

Rodar:

```bash
N8N_API_KEY=... python3 scripts/lara_production_readiness.py
```

Resultado correto antes do teste WhatsApp:

```text
status: BLOCKED
blockers: ["real_whatsapp_shadow_test"]
```

Checks que devem estar aprovados antes do teste real:

- `prod_webhook_unchanged`
- `shadow_webhook_active`
- `single_turn_actual_outputs`
- `multi_turn_journeys`
- `input_contract_payloads`
- `qa_side_effects_blocked`

Resultado necessario para promover:

```text
status: READY_FOR_PRODUCTION_APPROVAL
blockers: []
```

## Promocao

Somente depois do gate aprovado:

```bash
N8N_API_KEY=... python3 scripts/lara_prepare_production_promotion.py \
  --apply \
  --confirm 'PROMOVER LARA V9 PARA PRODUCAO'
```

## Decisao tecnica

Nao promover apenas com teste local. Nao promover apenas com QA simulado. O criterio minimo agora e conversa real pelo WhatsApp no webhook shadow, com evidencia salva.
