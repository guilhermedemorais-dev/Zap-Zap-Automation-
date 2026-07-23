# Lara V9 Goal Report - 2026-07-20

## Status

Status: parcial, ainda nao READY.

Motivo: LangGraph, CRM API, QA pelo n8n e jornada real sem `qa_mode` com numero
fake passaram nos pontos criticos testados. Falta a validacao final pela tela do
WhatsApp de teste/producao, porque o teste fake prova o caminho tecnico, mas nao
prova entrega real via UAZAPI com token do provedor.

## Alteracoes Aplicadas

- `lara_langgraph/graph.py`
  - adicionada persistencia de estado por `LARA_STATE_FILE`;
  - adicionada aceitacao de horario por extenso, como `pode ser as dez`;
  - corrigido resumo de agendamento para nao duplicar horario;
  - corrigida pontuacao entre motivo e preferencia.
  - corrigida abertura de agendamento com nome confirmado: quando o cliente ja
    informou o nome, a Lara responde `Perfeito, [nome]. Deixa eu verificar
    nossa agenda.` antes de acionar `check_availability`.
- `Dockerfile.langgraph`
  - configurado `LARA_STATE_FILE=/data/lara_sessions.json`;
  - criado diretorio `/data`.
- `docker-compose.langgraph.yml`
  - adicionado volume `lara_langgraph_data:/data`;
  - adicionada env `LARA_STATE_FILE`.
- VPS `/docker/n8n-zcac/docker-compose.yml`
  - adicionado volume `lara_langgraph_data:/data` no servico `lara-langgraph`;
  - recriado somente o container `lara-langgraph`.
- CRM API no VPS
  - imagem do `orion-crm-api-1` redeployada com codigo que preenche `leads.name`
    e `leads.email` no `create-appointment`.
- n8n workflow `LARA V9 Shadow SDR`
  - corrigidos retornos internos em `ROOT: Processar Comando` e
    `ROOT: Injetar Regras` que confundiam o validador do n8n MCP;
  - backup antes da alteracao:
    `backups/n8n-lara-v9-before-root-code-validator-fix-20260720-053748.json`.
  - corrigido `Code: Slots Para LangGraph`, que extraia `07:00` indevidamente
    da data `2026-07-21`;
  - backups do patch de slots:
    `backups/n8n-lara-v9-before-slot-parser-fix-20260720-055158.json` e
    `backups/n8n-lara-v9-after-slot-parser-fix-20260720-055158.json`.
  - adicionada telemetria honesta de envio nos nodes `Code: Enviar Blocos` e
    `Code: Enviar Pre-Blocos`, com `blocks_attempted`, `blocks_sent`,
    `send_success`, `send_errors` e `uazapi_token_present`;
  - backups do patch de telemetria:
    `backups/n8n-lara-v9-before-send-telemetry-20260720-060539.json` e
    `backups/n8n-lara-v9-after-send-telemetry-20260720-060539.json`.
- QA runner
  - `scripts/lara_n8n_qa_journey.py` agora usa numero fake unico por rodada
    com prefixo seguro `+550000000...`, evitando falso negativo por memoria
    LangGraph contaminada de testes anteriores.

## Evidencias

### Testes locais

Comando:

```bash
.venv-langgraph/bin/python -m unittest tests/test_lara_langgraph.py tests/test_lara_service.py -v
```

Resultado: `Ran 30 tests ... OK`.

### LangGraph remoto

Health de dentro do n8n:

```bash
docker exec n8n-zcac-n8n-1 wget -qO- http://lara-langgraph:8080/health
```

Resultado:

```json
{"status":"ok"}
```

Persistencia validada:

- sessao: `wa:+550000001130`;
- mensagem 1: `Boa noite`;
- mensagem 2: `Guilherme`;
- restart do container `lara-langgraph`;
- mensagem 3: `Fazer um agendamento`;
- resultado: `confirmed_name = Guilherme`, `conversation_stage = agenda_slots`,
  `next_action = check_availability`.

Horario por extenso validado:

- entrada: `pode ser as dez`;
- resultado: `pending_booking.time = 10:00`,
  `conversation_stage = agenda_contexto`.

Jornada completa direta validada:

- sessao: `wa:+550000001141`;
- fluxo: saudacao, nome, agendamento com erro de digitacao, slots, horario por
  extenso, motivo, preferencia, email, confirmacao de telefone, confirmacao final;
- resultado final: `next_action = create_appointment`;
- payload final:

```json
{
  "name": "Guilherme",
  "phone": "+550000001141",
  "date": "2026-07-21",
  "time": "10:00",
  "email": "guilherme.qa@example.com",
  "phone_confirmed": true,
  "reason": "quero ver alianças prontas com gravação interna para casamento",
  "interest": "alianças de casamento"
}
```

Resumo de confirmacao validado:

```text
Perfeito, Guilherme. Para confirmar: seu atendimento fica para 21/07 - 10:00.
Assunto do atendimento: quero ver alianças prontas com gravação interna para casamento. Preferência: joia pronta.
Confirma para mim se é isso mesmo?
```

Smoke remoto apos deploy:

- `onde fica a loja?` retorna o endereco oficial e o link do Google Maps;
- `quero falar com uma atendente` retorna `next_action = handoff`;
- mensagem seguinte na mesma sessao retorna `next_action = none`, porque
  `human_takeover = true`.

Smoke remoto apos correcao de abertura de agenda:

- sessao: `wa:+550000009003`;
- fluxo: `Boa noite`, `Guilherme`, `Fazer um agendamento`;
- resultado final: `conversation_stage = agenda_slots`,
  `next_action = check_availability`, `confirmed_name = Guilherme`;
- resposta final da etapa: `Perfeito, Guilherme. Deixa eu verificar nossa agenda.`
  e `Aguarde um momento, por favor.`

Smoke n8n de envio com payload fake sem token:

- execucao: `4181`;
- entrada: `onde fica a loja?`;
- Lara respondeu com endereco oficial e Maps;
- `Code: Enviar Blocos.blocks_attempted = 2`;
- `Code: Enviar Blocos.blocks_sent = 0`;
- `send_success = false`;
- `uazapi_token_present = false`;
- `send_errors` registrou `401 Missing token`.

Interpretação: antes desse patch, o fluxo marcava `blocks_sent = blocks.length`
mesmo quando a UAZAPI recusava o envio. Agora o QA consegue diferenciar resposta
gerada de mensagem realmente enviada.

### QA n8n multi-turn

Rodada em `qa_mode=true` no webhook ativo `whatsapp-inbound`, sem WhatsApp real
e sem CRM real:

- script: `.venv-langgraph/bin/python scripts/lara_n8n_qa_journey.py --ids JOURNEY-04 --delay 14`;
- execucoes: `4190`, `4192`, `4193`;
- resultado: `Journeys: 1/1 passed`;
- execucao critica: `4193`;
- entrada: `Gostaria de agendar um atendimento`;
- `Lara LangGraph Turn.confirmed_name = Guilherme`;
- `conversation_stage = agenda_slots`;
- `next_action = check_availability`;
- `Code: Parse Agent Output.type = action`;
- `Code: Parse Agent Output.action = check_availability`;
- `QA: Normalizar Output.side_effects_blocked = true`.

Observacao: uma rodada anterior com execucoes `4185`, `4186`, `4187` falhou por
memoria antiga no numero fake fixo `+550000000901`. O script foi ajustado para
usar numero fake unico por rodada. Isso tambem reforca que QA reutilizando o
mesmo numero precisa limpar estado antes do teste.

### CRM API

Health:

```json
{"status":"ok","db":"ok","redis":"ok"}
```

Slots reais testados de dentro do container n8n:

```http
GET https://api.crm.orinjoias.com/api/v1/n8n/webhook/available-slots?date=2026-07-21&next_available=true
GET http://api:4000/api/v1/n8n/webhook/available-slots?date=2026-07-21&next_available=true
```

Resultado dos dois caminhos:

```json
{
  "date": "2026-07-21",
  "day_name": "terça-feira",
  "slots": ["09:00", "10:00", "11:00"]
}
```

Endpoint testado de dentro do container n8n:

```http
POST http://api:4000/api/v1/n8n/webhook/create-appointment
```

Payload fake:

- WhatsApp: `+550000001121`;
- nome: `Guilherme QA V9`;
- e-mail: `guilherme.qa.v9@example.com`;
- data futura: `2099-01-02T12:00:00.000Z`.

Resultado HTTP: `201 Created`.

Retorno:

```json
{
  "accepted": true,
  "appointment_id": "37af091b-f685-4216-9ed0-26cb8165371c",
  "lead_id": "fe89dd5c-a9d8-4dc6-96f4-e923a0400af0",
  "starts_at": "2099-01-02T12:00:00.000Z",
  "reminder_scheduled": true
}
```

Banco:

- `leads.name = Guilherme QA V9`;
- `leads.email = guilherme.qa.v9@example.com`;
- `leads.stage = QUALIFICADO`;
- `appointments.status = AGENDADO`.

Jornada real sem `qa_mode` via webhook fake:

- numero: `+550000000153`;
- execucoes principais: `4173`, `4174`, `4179`;
- `4173`: CRM retornou slots reais `09:00`, `10:00`, `11:00`;
- `4173`: `Code: Slots Para LangGraph` normalizou somente `21/07 - 09:00`,
  `21/07 - 10:00`, `21/07 - 11:00`;
- `4174`: cliente escolheu `10:00`; Lara gerou `pending_booking` e pediu
  motivo da visita, sem criar appointment;
- `4179`: apos motivo, preferencia, e-mail, confirmacao do WhatsApp e
  confirmacao final, Lara gerou `action = create_booking`;
- `4179`: `CRM: Criar Appointment` retornou `accepted = true`,
  `appointment_id = eeacc0bd-bc93-4ec4-8b92-1a43381a4d12`,
  `lead_id = 3d8a07da-a850-4201-86aa-a348e38dab6f`;
- `4179`: resposta final usou endereco correto e Maps correto.

Banco para o appointment `eeacc0bd-bc93-4ec4-8b92-1a43381a4d12`:

- `appointments.status = AGENDADO`;
- `appointments.starts_at = 2026-07-21 13:00:00+00` equivalente a 10:00 BRT;
- `leads.whatsapp_number = +550000000153`;
- `leads.name = Guilherme`;
- `leads.email = guilherme.qa.v9.full@example.com`;
- `leads.stage = NOVO`, coerente com o fluxo agenda-primeiro informado;
- `appointments.notes` contem cliente, e-mail, WhatsApp confirmado e motivo;
- `appointments.ai_context` contem `interesse = alianças de casamento`,
  `visit_reason`, `customer_name`, `customer_email` e `phone_confirmed = true`.

### n8n QA mode

Execucoes:

- `4158`: `Boa noite`;
- `4159`: `Guilherme`;
- `4160`: `Fazer um agendamento`.

Execucao `4160`:

- `Global Variables.number = 550000000131`;
- `Get Message.message = Fazer um agendamento`;
- `Lara LangGraph Turn.confirmed_name = Guilherme`;
- `conversation_stage = agenda_slots`;
- `next_action = check_availability`;
- `Code: Parse Agent Output.type = action`;
- `action = check_availability`;
- `QA: Normalizar Output.side_effects_blocked = true`.

Nova rodada apos correcao dos nodes ROOT:

- `4165`: `Boa noite`;
- `4166`: `Guilherme`;
- `4167`: `Fazer um agendamento`.

Execucao `4167`:

- `Global Variables.number = 550000000151`;
- `Get Message.message = Fazer um agendamento`;
- `Lara LangGraph Turn.confirmed_name = Guilherme`;
- `conversation_stage = agenda_slots`;
- `next_action = check_availability`;
- `Code: Parse Agent Output.type = action`;
- `action = check_availability`;
- `action_args.date = 2026-07-21`;
- `action_args.next_available = true`;
- `QA: Normalizar Output.side_effects_blocked = true`.

## Validacao n8n

`n8n_validate_workflow` retornou `valid=true`.

Resumo:

```json
{
  "valid": true,
  "totalNodes": 146,
  "enabledNodes": 146,
  "triggerNodes": 2,
  "validConnections": 164,
  "invalidConnections": 0,
  "expressionsValidated": 128,
  "errorCount": 0,
  "warningCount": 16
}
```

Os 16 warnings restantes sao nos legados inalcançaveis e expressoes de nodes
antigos fora do caminho ativo. Nao bloqueiam o workflow publicado, mas devem ser
limpos depois para reduzir ruido de manutencao.

## Workflows Ativos

Lista ativa do n8n em 2026-07-20:

- `LARA V9 Shadow SDR`, id `7kXu17NYpsN8Yc65`, ativo.

Nao apareceu outro workflow ativo na listagem do n8n MCP.

## Pendencias Antes De READY

1. Rodar teste real pela tela do WhatsApp de teste/producao e confirmar que as
mensagens aparecem para o usuario, porque o teste fake nao prova entrega UAZAPI
com token real.
2. No teste real, conferir `uazapi_token_present = true`, `send_success = true`
e `blocks_sent = blocks_attempted` nas execucoes do n8n.
3. Trocar persistencia por arquivo para Postgres/Redis duravel quando houver
janela tecnica, porque arquivo resolve restart simples, mas nao e ideal para
concorrencia alta.
4. Confirmar no CRM visual que o appointment fake aparece na agenda e que o lead
entra no fluxo esperado.
5. Limpar warnings de nodes legados inalcançaveis para reduzir ruido de
manutencao, embora eles nao bloqueiem o caminho ativo validado.
