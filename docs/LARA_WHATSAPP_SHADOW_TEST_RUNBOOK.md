# Lara V9 - Runbook De Teste WhatsApp Shadow

## Objetivo

Validar a Lara V9 em conversa real de WhatsApp antes de qualquer promocao para producao.

Este teste e obrigatorio porque o QA remoto do n8n ja aprovou cenarios simulados, mas ainda nao prova comportamento real no WhatsApp, com UAZAPI, atraso de mensagem, tela do usuario e conversa humana.

## Ambiente

- Workflow shadow: `LARA V9 Shadow SDR`
- ID shadow: `7kXu17NYpsN8Yc65`
- Webhook shadow: `https://n8n-zcac.srv1478933.hstgr.cloud/webhook/whatsapp-inbound-v9-shadow`
- Workflow producao preservado: `ORION-WF-Bot-v7-LARA-SDR`
- ID producao: `7SucjAi8zU69sQuT`
- Webhook producao: `whatsapp-inbound`
- Numero de producao do cliente: `+55 47 9696-3593`

## Pre-condicoes

1. O numero de teste deve estar apontado para o webhook shadow.
2. O numero de producao nao deve ser usado para teste destrutivo.
3. O tester deve salvar print ou execution id do n8n para cada fluxo validado.
4. `qa/lara_whatsapp_shadow_test.json` deve comecar como `PENDING`.

## Roteiro Obrigatorio

### Fluxo 1 - Abertura e nome

Enviar:

```text
Boa noite
```

Esperado:

- Lara cumprimenta com boa noite.
- Lara se apresenta como consultora virtual da ORIN Joias.
- Lara pergunta o nome.
- Lara nao usa nome do perfil do WhatsApp.

Enviar:

```text
Jhonatan
```

Esperado:

- Lara responde `Prazer, Jhonatan` ou equivalente natural.
- Lara nao pergunta o nome novamente.
- Lara pergunta o que o cliente busca.

### Fluxo 2 - Atendimento presencial e agenda

Enviar:

```text
Quero atendimento presencial
```

Esperado:

- Lara indica que vai verificar agenda ou horarios.
- Nao confirma agendamento ainda.
- Nao envia endereco ainda.
- Nao pede e-mail antes de oferecer/verificar horario.

Enviar:

```text
Pode ser as 10
```

Esperado:

- Lara nao confirma agendamento.
- Lara pede dados que faltam, principalmente nome completo e motivo da visita.
- Lara nao cria appointment sem motivo.

### Fluxo 3 - Motivo da visita

Enviar:

```text
Meu nome completo e Jhonatan Silva. Quero ver alianças prontas com gravação interna para casamento.
```

Esperado:

- Lara reconhece o motivo.
- Lara resume o interesse do cliente.
- Lara pede confirmacao antes de finalizar agendamento, se ainda faltar algum dado.
- Lara nao inventa preco, estoque, prazo ou modelo.

### Fluxo 4 - Endereco

Enviar:

```text
Onde fica a loja?
```

Esperado:

- Endereco correto: `Av. Brasil, 1500 - Centro, Balneário Camboriú - SC, 88330-901`.
- Deve enviar Google Maps: `https://maps.app.goo.gl/geMC3hHsQqGfSnnm6`.
- Nao pode aparecer `Rua das Flores`.

### Fluxo 5 - Humano

Enviar:

```text
Quero falar com uma atendente
```

Esperado:

- Lara encaminha para especialista ou handoff.
- Lara nao insiste em resolver sozinha.
- Lara nao perde o contexto anterior.

## Criterios De Reprovacao

Reprovar imediatamente se acontecer qualquer item:

- repete abertura depois que o nome ja foi informado;
- chama o cliente pelo nome errado;
- usa nome do perfil como nome confirmado;
- inventa preco, estoque, prazo, produto ou disponibilidade;
- confirma agendamento sem motivo da visita;
- cria appointment antes de confirmacao;
- envia endereco errado;
- entra em loop de mensagens;
- responde em tom seco, confuso ou robotizado;
- dispara mensagens duplicadas.

## Registro Da Evidencia

Depois do teste, preencher `qa/lara_whatsapp_shadow_test.json`:

```json
{
  "status": "APPROVED",
  "tested_at": "2026-07-14T00:00:00-03:00",
  "tester": "Nome",
  "test_number": "+55 XX XXXXX-XXXX",
  "approved_by_user": true,
  "evidence": {
    "screenshots": ["/caminho/do/print.png"],
    "n8n_execution_ids": ["0000"],
    "notes": "Resumo curto do teste."
  },
  "checklist": {
    "greeting_asks_name_without_using_profile_name": true,
    "name_is_remembered_after_next_message": true,
    "appointment_intent_checks_availability_before_booking": true,
    "selected_time_without_reason_does_not_create_booking": true,
    "visit_reason_is_collected_before_confirmation": true,
    "address_is_correct_when_sent": true,
    "human_request_routes_to_specialist_or_handoff": true,
    "no_repeated_opening_loop": true,
    "no_wrong_customer_name": true,
    "no_obvious_hallucination": true
  },
  "failures": []
}
```

## Validacao Final

Rodar:

```bash
N8N_API_KEY=... python3 scripts/lara_production_readiness.py
```

Resultado esperado antes de producao:

```text
status: READY_FOR_PRODUCTION_APPROVAL
blockers: []
```

Depois disso, e somente depois disso, a promocao pode ser preparada com:

```bash
N8N_API_KEY=... python3 scripts/lara_prepare_production_promotion.py --apply --confirm 'PROMOVER LARA V9 PARA PRODUCAO'
```
