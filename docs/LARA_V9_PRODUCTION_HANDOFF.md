# Lara V9 - Handoff De Producao

## Resumo executivo

A Lara V9 ja esta criada e ativa no n8n remoto como workflow shadow. Ela ainda nao deve substituir a producao porque falta o teste real no WhatsApp apontado para o webhook shadow.

## Estado atual

- Producao atual preservada: `ORION-WF-Bot-v7-LARA-SDR`
- ID producao: `7SucjAi8zU69sQuT`
- Webhook producao: `whatsapp-inbound`
- Shadow V9 ativo: `LARA V9 Shadow SDR`
- ID shadow: `7kXu17NYpsN8Yc65`
- Webhook shadow: `whatsapp-inbound-v9-shadow`
- URL shadow: `https://n8n-zcac.srv1478933.hstgr.cloud/webhook/whatsapp-inbound-v9-shadow`
- Numero de producao do cliente: `+55 47 9696-3593`

## O que ja foi validado

- QA remoto do n8n contra output real do shadow: `22/22` cenarios passaram apos o patch de entrada.
- Execucoes single-turn atuais: `4008` a `4029`.
- QA multi-turn remoto do n8n: `3/3` jornadas passaram apos o patch de entrada.
- Execucoes multi-turn atuais: `4039` a `4047`.
- QA de contrato de entrada WhatsApp/provedor: `4/4` payloads passaram.
- Execucoes contrato de entrada: `3982` a `3985`.
- Payloads validados: UAZAPI atual, Evolution/Baileys `messages.upsert`, `data.text` e payload achatado defensivo.
- QA sem side effects: nenhuma execucao de teste rodou envio WhatsApp real, CRM real, agenda real ou save real do ROOT.
- Producao segue ativa e com webhook original.
- Promocao para producao esta bloqueada por script enquanto faltar evidencia WhatsApp real.

## O que ainda falta

O numero de teste precisa chamar o webhook shadow, nao a producao.

Depois disso, executar o roteiro em:

- `docs/LARA_WHATSAPP_SHADOW_TEST_RUNBOOK.md`

Se o WhatsApp real repetir abertura, errar nome, inventar informacao, confirmar agenda antes do motivo ou mandar endereco errado, a V9 reprova e deve ser corrigida no shadow.

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
