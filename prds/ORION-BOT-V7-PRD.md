# PRD — ORION Bot Lara SDR v7: Integração CRM + Workflow n8n

## Contexto

O ORION-WF-Bot-v7-LARA-SDR é um workflow n8n que implementa a Lara, uma SDR virtual da ORIN Joias. A Lara qualifica leads via WhatsApp (UAZAPI), coleta dados (ocasião, tipo de peça, material, urgência) usando SPIN adaptado, e agenda visitas presenciais/online.

O workflow v7 já está funcional para conversação com:
- Redis (buffer inteligente + cache de sessão)
- PostgreSQL (histórico permanente via tabela `chat_history`)  
- OpenAI GPT-4o (AI Agent principal) + GPT-4o-mini (Context Refiner)
- Groq Whisper (transcrição de áudio)
- Anti-loop, filtro fromMe, dividir resposta, reset *R

**O que falta:** integração com o CRM ORION para persistir dados de leads, agendar pelo CRM (não por Google Calendar), recuperar contexto quando Redis expira, e criar appointments com reminder automático.

---

## Repositório

```
ORION-CRM/
├── apps/
│   ├── api/
│   │   └── src/
│   │       ├── routes/
│   │       │   ├── n8n.routes.ts          ← MODIFICAR (adicionar 3 endpoints)
│   │       │   └── appointments.routes.ts  ← REFERÊNCIA (lógica de appointments)
│   │       ├── services/
│   │       │   └── inbox.service.ts        ← REFERÊNCIA (upsertConversation)
│   │       ├── workers/
│   │       │   └── appointmentReminder.worker.ts ← USAR (enqueue reminder)
│   │       ├── db/
│   │       │   ├── pool.ts                 ← USAR (query, transaction)
│   │       │   └── migrations/
│   │       │       ├── 003_leads_customers.sql
│   │       │       ├── 016_pipeline_upgrade.sql (lead_timeline)
│   │       │       ├── 017_pipelines_foundation.sql
│   │       │       └── 042_appointments.sql
│   │       ├── middleware/
│   │       │   └── audit.js                ← REFERÊNCIA
│   │       └── lib/
│   │           ├── logger.ts
│   │           └── errors.ts
│   └── web/ (frontend — não modificar)
└── PRD.DOCS/
```

---

## Arquitetura de dados relevante

### Tabela `leads`
```sql
id UUID PK, whatsapp_number VARCHAR(20) UNIQUE, name VARCHAR(255),
email VARCHAR(255), stage lead_stage (NOVO|QUALIFICADO|PROPOSTA_ENVIADA|NEGOCIACAO|CONVERTIDO|PERDIDO),
assigned_to UUID FK→users, source lead_source, notes TEXT,
pipeline_id UUID FK→pipelines, stage_id UUID FK→pipeline_stages,
converted_customer_id UUID FK→customers,
last_interaction_at TIMESTAMPTZ, created_at, updated_at
```

### Tabela `appointments`
```sql
id UUID PK, type VARCHAR(50), status VARCHAR(50) DEFAULT 'AGENDADO',
source VARCHAR(50) DEFAULT 'CRM', starts_at TIMESTAMPTZ, ends_at TIMESTAMPTZ,
notes TEXT, lead_id UUID FK→leads, customer_id UUID FK→customers,
assigned_to UUID FK→users, pipeline_id UUID FK→pipelines,
ai_context JSONB, cancelled_at TIMESTAMPTZ, cancel_reason VARCHAR(500),
reminder_sent_at TIMESTAMPTZ, created_at, updated_at
```

### Tabela `lead_timeline`
```sql
id UUID PK, lead_id UUID FK→leads, type VARCHAR(50),
title VARCHAR(255), body TEXT, created_by UUID FK→users,
created_at TIMESTAMPTZ
```

### Tabela `conversations` / `messages`
```sql
conversations: id, whatsapp_number, status (BOT|AGUARDANDO_HUMANO|RESOLVIDA), lead_id, last_message_at
messages: id, conversation_id FK, direction (INBOUND|OUTBOUND), type, content, is_automated, status
```

### Auth padrão n8n
Todos endpoints em `n8n.routes.ts` usam `assertN8nAuthorized(req)` que valida Bearer token via tabela `webhook_keys` ou `settings.internal_webhook_key` ou env `N8N_API_KEY`.

### BullMQ Worker existente
`appointmentReminder.worker.ts` — enfileira job com delay, envia WhatsApp 24h antes do appointment. Já funciona, só precisa ser chamado.

---

## Sprint 1 — Endpoints CRM para o Bot (PRIORIDADE MÁXIMA)
**Objetivo:** O workflow n8n consegue ler contexto do lead, buscar horários e criar agendamento via API.
**Arquivo:** `apps/api/src/routes/n8n.routes.ts`
**Tempo estimado:** 2-3h

### Task 1.1 — `GET /webhook/lead-context`

**Por que:** Quando o Redis expira (após 10min de inatividade) e o cliente volta, a Lara precisa recuperar o contexto do CRM. Sem isso, ela perde tudo e recomeça do zero.

**Query params:** `?whatsapp_number=+5547999210228`

**Lógica:**
1. Normalizar número com `normalizeWhatsapp()` (já existe no arquivo)
2. Buscar lead: `SELECT id, name, stage, notes, pipeline_id, stage_id, last_interaction_at FROM leads WHERE whatsapp_number = $1`
3. Buscar últimas 20 mensagens: `SELECT m.direction, m.content, m.created_at FROM messages m JOIN conversations c ON c.id = m.conversation_id WHERE c.whatsapp_number = $1 ORDER BY m.created_at DESC LIMIT 20`
4. Buscar próximo appointment ativo: `SELECT id, type, starts_at, status FROM appointments WHERE lead_id = $LEAD_ID AND status IN ('AGENDADO','CONFIRMADO_CLIENTE') AND starts_at > NOW() ORDER BY starts_at ASC LIMIT 1`
5. Tentar parsear `dados_coletados` do campo `notes` do lead (formato: `[bot] {"ocasiao":"casamento",...}`)

**Response 200:**
```json
{
  "lead": {
    "id": "uuid",
    "name": "Maria",
    "stage": "QUALIFICADO",
    "notes": "[bot] {\"ocasiao\":\"casamento\"}",
    "dados_coletados": {"ocasiao": "casamento"},
    "pipeline_id": "uuid",
    "stage_id": "uuid",
    "last_interaction_at": "2026-04-05T18:00:00Z"
  },
  "messages": [
    {"direction": "INBOUND", "content": "Oi", "created_at": "..."},
    {"direction": "OUTBOUND", "content": "Olá! ...", "created_at": "..."}
  ],
  "next_appointment": {
    "id": "uuid",
    "type": "VISITA_PRESENCIAL",
    "starts_at": "2026-04-10T14:00:00Z",
    "status": "AGENDADO"
  }
}
```

**Se lead não existe:** retorna `{ "lead": null, "messages": [], "next_appointment": null }`

**Schema Zod:**
```typescript
const leadContextQuery = z.object({
    whatsapp_number: z.string().trim().min(1).max(80),
});
```

**Usa:** `assertN8nAuthorized`, `normalizeWhatsapp`, `query` do pool

---

### Task 1.2 — `GET /webhook/available-slots`

**Por que:** A Lara precisa oferecer horários reais ao cliente. Sem isso, ela inventa horários ou não consegue agendar.

**Query params:** `?date=2026-04-10&period=tarde` (period é opcional)

**Lógica:**
1. Validar data (não pode ser passado, não pode ser domingo)
2. Buscar appointments do dia: `SELECT starts_at, ends_at FROM appointments WHERE starts_at >= $DATE_START AND starts_at < $DATE_END AND status NOT IN ('CANCELADO')`
3. Calcular slots disponíveis:
   - Seg-Sex: 9h-18h, slots de 45min a cada 60min
   - Sáb: 9h-13h
   - Dom: fechado (retornar erro)
4. Filtrar por período se informado (manha: <12h, tarde: >=12h)
5. Verificar max 2 simultâneos por slot
6. Retornar top 3 slots

**Response 200:**
```json
{
  "date": "2026-04-10",
  "day_name": "sexta-feira",
  "slots": ["14:00", "15:00", "16:00"],
  "message": "Na sexta-feira (10/04), tenho esses horários:\n\n1️⃣ 14:00\n2️⃣ 15:00\n3️⃣ 16:00\n\nQual prefere?"
}
```

**Se domingo:** `{ "date": "...", "slots": [], "message": "Aos domingos estamos fechados 😊 Que tal outro dia?" }`
**Se sem slots:** `{ "date": "...", "slots": [], "message": "Poxa, não tenho horário nesse dia 😔 Quer tentar outro dia?" }`

**Schema Zod:**
```typescript
const availableSlotsQuery = z.object({
    date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    period: z.enum(['manha', 'tarde']).optional(),
});
```

---

### Task 1.3 — `POST /webhook/create-appointment`

**Por que:** Quando o agendamento é confirmado, precisa criar o appointment no CRM com reminder automático 24h antes.

**Body:**
```json
{
  "whatsapp_number": "+5547999210228",
  "type": "VISITA_PRESENCIAL",
  "starts_at": "2026-04-10T14:00:00-03:00",
  "ends_at": "2026-04-10T14:45:00-03:00",
  "notes": "Interesse: aliança casamento ouro rosé",
  "ai_context": {"lead_score": 8, "dados_coletados": {"ocasiao": "casamento", "material": "ouro rosé"}}
}
```

**Lógica (usar `transaction()`):**
1. Normalizar número
2. Buscar lead pelo whatsapp_number (se não existe, criar como NOVO na pipeline 'leads')
3. Buscar pipeline default: `SELECT id FROM pipelines WHERE slug = 'leads' LIMIT 1`
4. Criar appointment:
   ```sql
   INSERT INTO appointments (type, status, source, starts_at, ends_at, notes, lead_id, pipeline_id, ai_context)
   VALUES ($1, 'AGENDADO', 'WHATSAPP_BOT', $2, $3, $4, $5, $6, $7)
   RETURNING id, starts_at
   ```
5. Atualizar lead stage para QUALIFICADO: `UPDATE leads SET stage = 'QUALIFICADO', stage_id = (SELECT id FROM pipeline_stages WHERE pipeline_id = $PID AND UPPER(REPLACE(name,' ','_')) = 'QUALIFICADO'), last_interaction_at = NOW() WHERE id = $LEAD_ID`
6. Registrar na lead_timeline:
   ```sql
   INSERT INTO lead_timeline (lead_id, type, title, body)
   VALUES ($1, 'APPOINTMENT_CREATED', 'Agendamento criado via bot', $2)
   ```
7. Enfileirar reminder BullMQ: `enqueueAppointmentReminderJob({ appointmentId, delayMs })` — delay = starts_at - 24h - now
8. Logar com `logger.info`

**Response 201:**
```json
{
  "accepted": true,
  "appointment_id": "uuid",
  "lead_id": "uuid",
  "starts_at": "2026-04-10T14:00:00-03:00",
  "reminder_scheduled": true
}
```

**Schema Zod:**
```typescript
const createAppointmentSchema = z.object({
    whatsapp_number: z.string().trim().min(1).max(80),
    type: z.string().default('VISITA_PRESENCIAL'),
    starts_at: z.string().min(1),
    ends_at: z.string().min(1),
    notes: z.string().max(4000).optional(),
    ai_context: z.record(z.unknown()).optional(),
});
```

**Importar:** `enqueueAppointmentReminderJob` de `../workers/appointmentReminder.worker.js`

---

## Sprint 2 — Conectar Workflow ao CRM (n8n)
**Objetivo:** O workflow v7 usa os novos endpoints para agendamento real.
**Tempo estimado:** 1-2h (no n8n, não no código)

### Task 2.1 — Adicionar node "CRM: Lead Context" no workflow
Depois do "Get chat_history From DataBase", adicionar fallback:
- HTTP GET `https://api.crm.orinjoias.com/api/v1/n8n/webhook/lead-context?whatsapp_number=+{number}`
- Auth: ORION API (id=Tcdgn0M6JbqsIVM0)
- Se retornar dados, injetar no histórico do Context Refiner

### Task 2.2 — Adicionar node "CRM: Buscar Slots" no workflow
Quando a Lara detectar intenção de agendamento com data:
- HTTP GET `https://api.crm.orinjoias.com/api/v1/n8n/webhook/available-slots?date={data}&period={periodo}`
- Injetar slots no prompt do AI Agent

### Task 2.3 — Adicionar node "CRM: Criar Appointment" no workflow
Quando agendamento for confirmado (data + horário):
- HTTP POST `https://api.crm.orinjoias.com/api/v1/n8n/webhook/create-appointment`
- Body com dados coletados + ai_context

### Task 2.4 — Adicionar lógica de handoff completo
Quando classificação = HANDOFF:
- Gerar código de retomada (4 dígitos)
- Enviar msg ao cliente com código
- Notificar atendente (5522998911070) com resumo
- POST CRM handoff

---

## Sprint 3 — Melhorias e testes (PÓS-DEPLOY)
**Objetivo:** Polir a experiência e garantir robustez.
**Tempo estimado:** 2-3h

### Task 3.1 — Testes end-to-end
Testar 10 cenários via WhatsApp real:
1. "Oi, vocês fazem aliança?" → qualificação natural
2. "Quero agendar pra amanhã às 14h" → resolve data + horário
3. "Já falei que é pra casamento" → Context Refiner encontra
4. Cliente volta depois de 2h → Redis expirou → CRM fallback
5. 15+ mensagens → handoff automático
6. Áudio → Whisper transcreve → responde
7. Imagem de joia → GPT-4o descreve → responde
8. "Vocês fazem bolo?" → fuga de assunto
9. *R → reset funciona
10. Agendamento completo → appointment no CRM + reminder 24h

### Task 3.2 — Avaliação NPS (opcional, Sprint futura)
Após encerramento de conversa qualificada:
- Enviar "De 1 a 5, como foi nosso atendimento?"
- Registrar nota no CRM

### Task 3.3 — Menu de boas-vindas (opcional)
Primeira mensagem do cliente recebe menu:
```
💎 Bem-vinda à ORIN Joias!
1️⃣ Catálogo de peças
2️⃣ Agendar visita
3️⃣ Dúvidas
```
Pode ser adicionado como IF no início do fluxo: se `chat_history` está vazio → enviar menu → setar estado.

### Task 3.4 — Dashboard de métricas
- Total de conversas/dia
- Taxa de qualificação (QUALIFICADO/total)
- Taxa de agendamento
- Tempo médio de conversa
- Top motivos de handoff

---

## Definição de Pronto por Sprint

### Sprint 1 ✅ quando:
- [ ] `curl GET /webhook/lead-context?whatsapp_number=+5547999210228` retorna JSON válido
- [ ] `curl GET /webhook/available-slots?date=2026-04-10` retorna slots reais
- [ ] `curl POST /webhook/create-appointment` cria appointment + agenda reminder
- [ ] Todos endpoints usam `assertN8nAuthorized`
- [ ] Testes com curl passam sem erro 500

### Sprint 2 ✅ quando:
- [ ] Lara oferece horários reais do CRM (não inventa)
- [ ] Agendamento confirmado aparece na tabela `appointments`
- [ ] Reminder BullMQ enfileirado (verificar Redis queue)
- [ ] Handoff notifica atendente + registra no CRM

### Sprint 3 ✅ quando:
- [ ] 10/10 cenários de teste passam
- [ ] Nenhuma alucinação em 20 conversas de teste
- [ ] Nenhum "Qual dia funciona?" quando cliente já informou data

---

## Referências de código

### Como adicionar endpoint em n8n.routes.ts (padrão existente):
```typescript
router.get(
    '/webhook/lead-context',
    async (req: Request, res: Response, next: NextFunction): Promise<void> => {
        try {
            await assertN8nAuthorized(req);
            // ... lógica aqui
            res.json({ ... });
        } catch (error) {
            next(error);
        }
    }
);
```

### Como usar transaction (de pool.ts):
```typescript
import { query, transaction } from '../db/pool.js';
const result = await transaction(async (client) => {
    const lead = await client.query('SELECT ...');
    const appt = await client.query('INSERT INTO appointments ...');
    return appt.rows[0];
});
```

### Como enfileirar reminder:
```typescript
import { enqueueAppointmentReminderJob } from '../workers/appointmentReminder.worker.js';
const startsAtMs = new Date(starts_at).getTime();
const reminderDelay = startsAtMs - 24 * 60 * 60 * 1000 - Date.now();
if (reminderDelay > 0) {
    await enqueueAppointmentReminderJob({ appointmentId: id, delayMs: reminderDelay });
}
```

### normalizeWhatsapp (já existe no arquivo):
```typescript
function normalizeWhatsapp(input: string): string {
    const trimmed = input.trim();
    if (trimmed.startsWith('+')) return `+${trimmed.slice(1).replace(/\D/g, '')}`;
    const digits = trimmed.replace(/\D/g, '');
    if (digits.length >= 10 && digits.length <= 11) return `+55${digits}`;
    return `+${digits}`;
}
```

---

## Comando para o Claude Code CLI

```bash
# Sprint 1 — executar no root do ORION-CRM
claude "Leia o arquivo PRD.DOCS/ORION-BOT-V7-PRD.md e execute a Sprint 1. 
Adicione os 3 endpoints (lead-context, available-slots, create-appointment) 
em apps/api/src/routes/n8n.routes.ts seguindo o padrão dos endpoints existentes.
Use assertN8nAuthorized, normalizeWhatsapp, query/transaction do pool.
Importe enqueueAppointmentReminderJob para o create-appointment.
Teste com exemplos de curl no final."
```
