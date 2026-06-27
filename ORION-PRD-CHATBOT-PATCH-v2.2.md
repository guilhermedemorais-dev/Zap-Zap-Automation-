# ORION — PRD: Patch Chatbot v2.2 (Definitivo)

**Tipo:** PATCH — corrigir nós existentes no workflow  
**Arquivo:** `ORION-WF-Bot-Qualificacao-WhatsApp.json`  
**Nós afetados:** 11 modificados + 5 novos  

---

## CORREÇÃO 1 — System Prompt da Lara

### Nó: `09 — Preparar Payload Groq`

Substituir a `const systemPrompt` inteira por:

```javascript
const isFirstMessage = history.length === 0;
const menuLabel = {
    'catalogo': 'Catálogo de peças',
    'agendamento': 'Agendar visita',
    'duvidas': 'Dúvidas',
    'texto_livre': null
}[menu_option] ?? null;

const systemPrompt = `IDENTIDADE:
Você é Lara, consultora da ORIN Joias — joalheria de design autoral e produção artesanal em Balneário Camboriú. Atendimento premium, humano, direto. Você atua como SDR de luxo: entende o contexto, qualifica o lead e direciona para catálogo ou agendamento.

FORMATO DE RESPOSTA (sempre JSON válido, sem markdown):
{
  "resposta": "texto pro cliente",
  "classificacao": "QUALIFICADO" | "CURIOSO" | "AGENDAMENTO" | "HANDOFF" | "CONTINUAR",
  "dados_coletados": {
    "nome": null,
    "instagram": null,
    "interesse": null,
    "material": null,
    "ocasiao": null,
    "orcamento": null,
    "urgencia": null,
    "cidade": null
  },
  "resumo_lead": null,
  "encerrar": false,
  "etapa_qualificacao": "ocasiao" | "tipo" | "material" | "timing" | "decisao" | "completa"
}

REGRA DE ABERTURA:
${isFirstMessage ? `Esta é a PRIMEIRA interação após o menu. Comece assim:
"Olá! Sou a Lara, da ORIN Joias ✨ Se quiser voltar ao menu, é só me avisar.${menuLabel ? `\\n\\nVi que você escolheu *${menuLabel}*. ` : '\\n\\n'}[puxar assunto direto da opção escolhida]"
Exemplo catálogo: "...Vi que você escolheu *Catálogo de peças*. Está buscando algo pra uma ocasião especial ou uso no dia a dia?"
Exemplo agendamento: "...Vi que você escolheu *Agendar visita*. Que ótimo! Tem algum dia da semana que funciona melhor pra você?"
Exemplo dúvidas: "...Vi que você escolheu *Dúvidas*. Pode mandar — estou aqui pra ajudar!"` :
`Conversa JÁ em andamento. NUNCA se apresente. NUNCA diga Olá/Oi. Vá DIRETO ao ponto.`}

ESTILO DE COMUNICAÇÃO:
- 1 a 3 linhas por mensagem. Máximo 4 se precisar de contexto.
- Máximo 1 emoji por mensagem: 💎 ✨ 💛
- 1 pergunta por vez. NUNCA duas na mesma mensagem.
- NUNCA use o nome do cliente. Trate como "você". Única exceção: se acabou de dizer o nome, use 1 vez como reconhecimento.
- Tom: elegante, acessível, caloroso. Consultora premium — não robô, não telemarketing.
- NUNCA revele que é IA/bot/assistente virtual. Você é a Lara, pessoa real.
- NUNCA prometa preço, prazo ou desconto.
- NUNCA peça CPF, RG, endereço ou dados bancários.
- NUNCA repita pergunta já respondida — sempre avance.
- Se a informação já está no histórico, NÃO pergunte de novo.

FLUXO DE QUALIFICAÇÃO (seguir esta ordem, 1 etapa por vez):
1. OCASIÃO → "É pra uma ocasião especial ou uso no dia a dia?" / "É pra você ou pra presentear?"
2. TIPO DE PEÇA → "Que tipo de peça está buscando? Anel, colar, brinco..." 
3. MATERIAL → "Tem preferência de material? Ouro amarelo, branco, rosé..."
4. TIMING → "E pra quando seria? Tem alguma data especial chegando?"

Regras do fluxo:
- Nunca pular etapa, nunca repetir.
- Máximo 2 mensagens por etapa. Se em 2 msgs o cliente não deu a info, avance pra próxima.
- Se o cliente já deu a info espontaneamente, pule a etapa.
- Registre a etapa atual em "etapa_qualificacao".

DECISÃO (após coletar pelo menos ocasião + tipo):
- Se tem interesse concreto → enviar catálogo:
  "Separei algumas opções que combinam com o que você busca: https://crm.orinjoias.com/loja ✨ Quer que eu selecione algumas peças pra você?"
  Classificar como QUALIFICADO.

- Se quer ver pessoalmente ou precisa de ajuda presencial → conduzir agendamento:
  1. "Tem algum dia da semana que funciona melhor pra você?"
  2. "Manhã ou tarde?"
  Classificar como AGENDAMENTO.

COLETA DE DADOS (sutil, nunca direta):
- NÃO pergunte "qual seu nome?" ou "me passa seu Instagram".
- Formas sutis:
  "E pra eu separar referências, tem Instagram?" → pega instagram
  "É pra você ou pra presentear?" → pega ocasião
  "Tem preferência de metal?" → pega material
- O pushName do WhatsApp JÁ está como nome no contexto. Use-o. Não pergunte nome.

QUANDO NÃO SOUBER RESPONDER:
- NÃO inventar. Dizer:
  "Essa é bem específica — vou pedir pra nossa equipe te responder certinho. Quer agendar um horário na loja pra tirar essa dúvida pessoalmente?"
- Classificar como AGENDAMENTO.

FUGA DE ASSUNTO:
- 1ª msg off-topic: humor leve + redireciona: "Haha, essa eu não sei 😄 Mas se quiser ver umas peças lindas: https://www.instagram.com/orinjoias/"
- 2ª msg off-topic: corta e volta: "Adoro conversar! Mas sou especialista em joias 💎 Posso te ajudar com alguma peça?"
- 3ª msg off-topic: encerrar. classificacao=CURIOSO, encerrar=true.

CLASSIFICAÇÃO:
- QUALIFICADO: tem ocasião + tipo de peça. Mostrou intenção real.
- CURIOSO: só preço genérico, sem contexto, ou 3+ trocas sem avanço.
- AGENDAMENTO: quer visitar, agendar, ou IA não resolve a dúvida.
- HANDOFF: pediu humano explicitamente, reclamação, pós-venda, troca, defeito.
- CONTINUAR: ainda qualificando, precisa de mais info.

resumo_lead: se QUALIFICADO/CURIOSO/AGENDAMENTO, preencha com ≤100 chars.
Ex: "Quer anel noivado ouro 18k, casamento 2 meses, orçamento ~5k"

Hoje é: ${today}`;
```

### Atualizar `userContent` no mesmo nó:

```javascript
let menuCtx = '';
if (menu_option === 'catalogo')     menuCtx = '[Cliente escolheu: CATÁLOGO]\n';
else if (menu_option === 'agendamento') menuCtx = '[Cliente escolheu: AGENDAMENTO]\n';
else if (menu_option === 'duvidas')     menuCtx = '[Cliente escolheu: DÚVIDAS]\n';
else if (menu_option === 'texto_livre') menuCtx = '[Cliente enviou texto livre]\n';

const resumedCtx = data.resumed_summary
    ? `[RETOMADA] Contexto anterior: ${data.resumed_summary}\nContinue de onde pararam.\n\n`
    : '';

const userContent = resumedCtx + menuCtx + historyText + `Nome: ${profile_name}\nMensagem: ${content}`;
```

---

## CORREÇÃO 2 — Handoff Camuflado (mensagem pro CLIENTE)

### Nó `08a — Handoff: Msg ao Cliente` (anti-loop)

**ANTES deste nó**, inserir novo nó `Handoff: Gerar Código` (ver CORREÇÃO 4).

Trocar jsonBody para:
```json
={
  "number": "{{ $json.whatsapp_number.replace('+','') }}",
  "text": "Obrigada pelo seu interesse! 💎\n\nPara continuar com uma das nossas consultoras, salve seu código: *{{ $json.handoff_code }}*\n\nInforme esse código quando nos enviar uma mensagem.\nTel: (47) 9921-0228\n\nFoi um prazer conversar com você ✨"
}
```

### Nó `15a — Handoff: Msg ao Cliente` (classificação HANDOFF)

Trocar jsonBody para:
```json
={
  "number": "{{ $json.whatsapp_number.replace('+','') }}",
  "text": "Entendi! Vou te encaminhar para uma das nossas especialistas 💎\n\nSeu código de atendimento: *{{ $json.handoff_code }}*\n\nEm instantes alguém vai te chamar aqui mesmo ✨"
}
```

---

## CORREÇÃO 3 — Handoff pro CRM + WhatsApp Atendente (CONTEXTO RICO)

O handoff deve fazer 3 coisas simultâneas:
1. Mensagem WhatsApp pro atendente (com contexto)
2. Chamar API do CRM pra atualizar conversa → `AGUARDANDO_HUMANO` (aparece no inbox kanban)
3. Atualizar lead no CRM com tag + dados coletados

### Nó `08b — Handoff: Notificar Atendente` (anti-loop)

Trocar jsonBody para:
```json
={
  "number": "5522998911070",
  "text": "📋 *Novo lead pra atendimento*\n\n👤 {{ $json.profile_name ?? 'Cliente' }}\n📱 {{ $json.whatsapp_number }}\n🔑 Código: {{ $json.handoff_code }}\n\n💬 {{ $json.dados_coletados?.interesse ? 'Interesse: ' + $json.dados_coletados.interesse : 'Interesse não identificado' }}\n{{ $json.dados_coletados?.material ? '✨ Material: ' + $json.dados_coletados.material + '\\n' : '' }}{{ $json.dados_coletados?.ocasiao ? '💒 Ocasião: ' + $json.dados_coletados.ocasiao + '\\n' : '' }}{{ $json.dados_coletados?.orcamento ? '💰 Orçamento: ' + $json.dados_coletados.orcamento + '\\n' : '' }}\n📝 {{ $json.resumo_lead ?? 'Bot encerrou por limite de mensagens.' }}\n\n➡️ wa.me/{{ $json.whatsapp_number.replace('+','') }}"
}
```

### Nó `15b — Handoff: Notificar Atendente` (classificação HANDOFF)

Trocar jsonBody para:
```json
={
  "number": "5522998911070",
  "text": "📋 *Novo lead pra atendimento*\n\n👤 {{ $json.profile_name ?? 'Cliente' }}\n📱 {{ $json.whatsapp_number }}\n🔑 Código: {{ $json.handoff_code }}\n🏷️ {{ $json.classificacao }}\n\n💬 {{ $json.dados_coletados?.interesse ? 'Interesse: ' + $json.dados_coletados.interesse : 'Interesse não identificado' }}\n{{ $json.dados_coletados?.material ? '✨ Material: ' + $json.dados_coletados.material + '\\n' : '' }}{{ $json.dados_coletados?.ocasiao ? '💒 Ocasião: ' + $json.dados_coletados.ocasiao + '\\n' : '' }}\n📝 {{ $json.resumo_lead ?? 'Cliente solicitou atendimento humano.' }}\n\n➡️ wa.me/{{ $json.whatsapp_number.replace('+','') }}"
}
```

### Nó `CRM: Handoff` — ENRIQUECER o body

Trocar jsonBody para:
```json
={
  "whatsapp_number": "{{ $json.whatsapp_number }}",
  "reason": "{{ $json.classificacao ?? 'anti-loop' }}",
  "resumo_ia": "{{ $json.resumo_lead ?? 'Sem resumo' }}",
  "dados_coletados": {{ JSON.stringify($json.dados_coletados ?? {}) }},
  "handoff_code": "{{ $json.handoff_code }}",
  "tags": ["{{ $json.classificacao === 'HANDOFF' ? 'duvida-cliente' : ($json.classificacao === 'CURIOSO' ? 'curioso' : 'qualificado') }}"]
}
```

### Nó `CRM: Handoff (Anti-Loop)` — ENRIQUECER o body

Trocar jsonBody para:
```json
={
  "whatsapp_number": "{{ $json.whatsapp_number }}",
  "reason": "anti-loop",
  "resumo_ia": "{{ $json.resumo_lead ?? 'Bot atingiu limite. Cliente precisa de atendimento humano.' }}",
  "dados_coletados": {{ JSON.stringify($json.dados_coletados ?? {}) }},
  "handoff_code": "{{ $json.handoff_code }}",
  "tags": ["anti-loop"]
}
```

### Nó `CRM: Atualizar Lead` — ADICIONAR tag

Trocar jsonBody para:
```json
={
  "whatsapp_number": "{{ $json.whatsapp_number }}",
  "stage": "{{ ['QUALIFICADO','AGENDAMENTO','HANDOFF'].includes($json.classificacao) ? 'QUALIFICADO' : 'NOVO' }}",
  "interest": "{{ $json.dados_coletados?.interesse ?? '' }}",
  "dados_coletados": {{ JSON.stringify($json.dados_coletados ?? {}) }},
  "tags": ["{{ $json.classificacao === 'CURIOSO' ? 'curioso' : ($json.classificacao === 'HANDOFF' ? 'duvida-cliente' : '') }}"],
  "resumo_ia": "{{ $json.resumo_lead ?? '' }}"
}
```

---

## CORREÇÃO 4 — Gerar Código de Retomada

### Novo nó: `Handoff: Gerar Código` (Code)

Posição: ANTES dos nós `08a` e `15a`. Os dois caminhos de handoff (anti-loop e classificação) passam por este nó primeiro.

```javascript
const data = $input.first().json;
const number = data.whatsapp_number;
const staticData = $getWorkflowStaticData('global');

// Gerar código 4 dígitos
const code = Math.floor(1000 + Math.random() * 9000).toString();

// Salvar código + contexto
if (!staticData.handoffCodes) staticData.handoffCodes = {};
staticData.handoffCodes[code] = {
    whatsapp_number: number,
    profile_name: data.profile_name,
    created_at: Date.now(),
    context: {
        dados_coletados: data.dados_coletados ?? {},
        classificacao: data.classificacao ?? 'HANDOFF',
        resumo_lead: data.resumo_lead ?? null,
        last_messages: (staticData.chatHistory?.[number] ?? []).slice(-10),
        menu_option: data.chat_state?.menu_option_chosen ?? null
    }
};

// Limpar códigos > 72h
const EXPIRY = 72 * 3600 * 1000;
for (const [k, v] of Object.entries(staticData.handoffCodes)) {
    if (Date.now() - v.created_at > EXPIRY) delete staticData.handoffCodes[k];
}

// Marcar conversa como ENCERRADA
if (staticData.chatState?.[number]) {
    staticData.chatState[number].status = 'ENCERRADA';
    staticData.chatState[number].handoff_code = code;
}

return [{ json: { ...data, handoff_code: code } }];
```

---

## CORREÇÃO 5 — Menu com Opção 7

### Nó `Menu: Boas-Vindas`

Trocar jsonBody para:
```json
={
  "number": "{{ $json.whatsapp_number.replace('+', '') }}",
  "text": "💎 Bem-vinda à *ORIN Joias*!\n\nSomos uma joalheria de design autoral e produção artesanal.\n\nComo posso te ajudar?\n\n1️⃣ Sobre nós\n2️⃣ Catálogo de peças\n3️⃣ Agendar visita\n4️⃣ Endereço\n5️⃣ Redes sociais\n6️⃣ Dúvidas\n7️⃣ Continuar atendimento anterior\n\nDigite o número da opção ✨"
}
```

### Nó `Menu: Mapear Escolha`

Adicionar ao `numberMap`:
```javascript
'7': 'retomar',
```

### Nó `Switch: Opção Menu`

Adicionar output `retomar` que conecta ao novo nó `Retomar: Pedir Código`.

---

## CORREÇÃO 6 — Fluxo de Retomada (Nós Novos)

### Novo nó: `Retomar: Pedir Código` (httpRequest)
```json
={
  "number": "{{ $json.whatsapp_number.replace('+', '') }}",
  "text": "Claro! 💎 Me informa o código de 4 dígitos que você recebeu no último atendimento."
}
```

### Novo nó: `Estado: Set AGUARDANDO_CODIGO` (Code)
```javascript
const staticData = $getWorkflowStaticData('global');
const data = $input.first().json;
const number = data.whatsapp_number;
if (!staticData.chatState) staticData.chatState = {};
staticData.chatState[number] = {
    ...(staticData.chatState[number] ?? {}),
    status: 'AGUARDANDO_CODIGO',
    last_activity_at: Date.now()
};
return [{ json: data }];
```

### Atualizar nó `Estado: Carregar` — adicionar lógica AGUARDANDO_CODIGO

Após o bloco de `menuKw` (reset pra menu), adicionar:

```javascript
// Processar código de retomada
if (state && state.status === 'AGUARDANDO_CODIGO') {
    const code = content.replace(/\D/g, '');
    if (code.length === 4 && staticData.handoffCodes?.[code]) {
        const saved = staticData.handoffCodes[code];
        // Restaurar histórico
        if (saved.context.last_messages && saved.context.last_messages.length > 0) {
            if (!staticData.chatHistory) staticData.chatHistory = {};
            staticData.chatHistory[number] = saved.context.last_messages;
        }
        // Restaurar estado
        staticData.chatState[number] = {
            status: 'ATENDIMENTO_IA',
            menu_option_chosen: saved.context.menu_option ?? 'duvidas',
            last_activity_at: Date.now(),
            inactivity_warning_sent: false
        };
        delete staticData.handoffCodes[code];
        return [{
            json: {
                ...data,
                chat_state: staticData.chatState[number],
                state_status: 'ATENDIMENTO_IA',
                resumed: true,
                resumed_summary: saved.context.resumo_lead
            }
        }];
    } else {
        // Código inválido
        return [{
            json: {
                ...data,
                state_status: 'CODIGO_INVALIDO',
                chat_state: state
            }
        }];
    }
}
```

### Atualizar nó `Switch: Estado Conversa`

Adicionar outputs:
- `AGUARDANDO_CODIGO` → já processado no Estado: Carregar (retorna ATENDIMENTO_IA ou CODIGO_INVALIDO)
- `CODIGO_INVALIDO` → novo nó

### Novo nó: `Retomar: Código Inválido` (httpRequest)
```json
={
  "number": "{{ $json.whatsapp_number.replace('+', '') }}",
  "text": "Não encontrei esse código 😕\n\nSe quiser, posso te ajudar com um novo atendimento!\n\nDigite *menu* pra ver as opções ✨"
}
```

### Novo nó: `Retomar: Bem-Vinda de Volta` (httpRequest)

Quando código é válido, ANTES de ir pra IA:
```json
={
  "number": "{{ $json.whatsapp_number.replace('+', '') }}",
  "text": "Que bom ter você de volta! 💎 Retomando de onde paramos..."
}
```

---

## CORREÇÃO 7 — Backend CRM (endpoint handoff)

O endpoint `POST /api/v1/n8n/webhook/handoff` no backend (`apps/api/src/routes/n8n.routes.ts`) precisa aceitar os novos campos:

### Atualizar Zod schema do handoff:

```typescript
const handoffSchema = z.object({
    whatsapp_number: z.string().trim().min(8).max(25),
    reason: z.string().trim().max(100),
    resumo_ia: z.string().trim().max(2000).optional(),
    dados_coletados: z.record(z.unknown()).optional(),
    handoff_code: z.string().max(10).optional(),
    tags: z.array(z.string().max(50)).max(10).optional(),
});
```

### Lógica do endpoint (o que deve fazer):

```typescript
// 1. Encontrar/criar conversa
const conversation = await upsertConversationFromInbound({
    meta_message_id: `handoff-${Date.now()}`,
    whatsapp_number: normalizeWhatsapp(parsed.data.whatsapp_number),
    type: 'TEXT',
    content: `[HANDOFF] ${parsed.data.resumo_ia ?? parsed.data.reason}`,
    media_url: null,
    profile_name: parsed.data.whatsapp_number,
    received_at: new Date().toISOString(),
});

// 2. Atualizar status da conversa → AGUARDANDO_HUMANO
await query(
    `UPDATE conversations SET status = 'AGUARDANDO_HUMANO', updated_at = NOW() WHERE id = $1`,
    [conversation.id]
);

// 3. Atualizar lead com resumo + tags
const lead = await query(
    `SELECT id FROM leads WHERE whatsapp_number = $1 LIMIT 1`,
    [normalizeWhatsapp(parsed.data.whatsapp_number)]
);
if (lead.rows[0]) {
    await query(
        `UPDATE leads SET 
            notes = COALESCE(notes, '') || E'\n\n[Bot] ' || $2,
            updated_at = NOW()
         WHERE id = $1`,
        [lead.rows[0].id, parsed.data.resumo_ia ?? parsed.data.reason]
    );
}

// 4. Responder
res.status(202).json({
    accepted: true,
    conversation_id: conversation.id,
    status: 'AGUARDANDO_HUMANO'
});
```

**Resultado no CRM:** a conversa aparece no inbox com status `AGUARDANDO_HUMANO`. O atendente vê no kanban, clica "Assumir", e tem acesso ao histórico + resumo da IA.

---

## MAPA DE CONEXÕES ATUALIZADO

```
[Anti-loop: 10+ msgs?] ── SIM ──→ [Handoff: Gerar Código] → [08a Msg Cliente] + [08b Notificar Atendente] + [CRM: Handoff (Anti-Loop)]

[Switch: Classificação]
  ├── HANDOFF → [Handoff: Gerar Código] → [15a Msg Cliente] + [15b Notificar Atendente] + [CRM: Handoff]
  ├── QUALIFICADO → [CRM: Atualizar Lead] + [CRM: Handoff] (atendente assume)
  ├── CURIOSO → [CURIOSO: Despedida] → [Avaliação: Pedir Nota]
  ├── AGENDAMENTO → [A1: Switch Agendamento]
  └── CONTINUAR → NoOp

[Switch: Opção Menu]
  ├── 1-5 → (sem mudança)
  ├── 6 duvidas → [Estado: Set ATENDIMENTO_IA] → [Preparar Payload Groq]
  ├── 7 retomar → [Retomar: Pedir Código] → [Estado: Set AGUARDANDO_CODIGO]
  └── texto_livre → [Estado: Set ATENDIMENTO_IA] → [Preparar Payload Groq]

[Switch: Estado Conversa]
  ├── NOVO/ENCERRADA → [Menu: Boas-Vindas]
  ├── MENU_ENVIADO → [Menu: Mapear Escolha]
  ├── ATENDIMENTO_IA → [Anti-Loop] → [Preparar Payload Groq]
  ├── AGUARDANDO_AVALIACAO → [Avaliação: Processar]
  ├── AGUARDANDO_CODIGO → (processado no Estado: Carregar)
  │     ├── código válido → [Retomar: Bem-Vinda de Volta] → [Preparar Payload Groq]
  │     └── código inválido → [Retomar: Código Inválido]
  └── HANDOFF → ignorar
```

---

## CHECKLIST DE MODIFICAÇÕES

| # | Nó | Ação | Seção |
|---|-----|------|-------|
| 1 | `09 — Preparar Payload Groq` | SUBSTITUIR systemPrompt + userContent | C1 |
| 2 | `08a — Handoff: Msg ao Cliente` | TROCAR jsonBody (camuflado + código) | C2 |
| 3 | `15a — Handoff: Msg ao Cliente` | TROCAR jsonBody (camuflado + código) | C2 |
| 4 | `08b — Handoff: Notificar Atendente` | TROCAR jsonBody (contexto rico) | C3 |
| 5 | `15b — Handoff: Notificar Atendente` | TROCAR jsonBody (contexto rico) | C3 |
| 6 | `CRM: Handoff` | ENRIQUECER jsonBody (+dados, +tags, +código) | C3 |
| 7 | `CRM: Handoff (Anti-Loop)` | ENRIQUECER jsonBody (+dados, +tags, +código) | C3 |
| 8 | `CRM: Atualizar Lead` | ADICIONAR tags + resumo | C3 |
| 9 | `Menu: Boas-Vindas` | ADICIONAR opção 7 | C5 |
| 10 | `Menu: Mapear Escolha` | ADICIONAR '7': 'retomar' | C5 |
| 11 | `Switch: Opção Menu` | ADICIONAR output retomar | C5 |
| 12 | `Estado: Carregar` | ADICIONAR lógica AGUARDANDO_CODIGO | C6 |
| 13 | `Switch: Estado Conversa` | ADICIONAR output CODIGO_INVALIDO | C6 |
| **NOVOS** | | |
| N1 | `Handoff: Gerar Código` (Code) | CRIAR | C4 |
| N2 | `Retomar: Pedir Código` (httpRequest) | CRIAR | C6 |
| N3 | `Estado: Set AGUARDANDO_CODIGO` (Code) | CRIAR | C6 |
| N4 | `Retomar: Código Inválido` (httpRequest) | CRIAR | C6 |
| N5 | `Retomar: Bem-Vinda de Volta` (httpRequest) | CRIAR | C6 |

---

## O QUE NÃO MEXER

- Buffer Redis (nós 04, 05, 06)
- Validação de payload (nó 03)
- Webhook inbound (nó 01)
- Responder 200 (nó 02)
- Respostas automáticas (Sobre nós, Endereço, Redes Sociais, Catálogo)
- Avaliação (processar, obrigada, pedir nota)
- CRM: Registrar Mensagem / Bot Reply
- Nós M5 (Áudio) e M6 (Sheets) — pendentes
- Nós de agendamento (A1-A9) — são outro escopo
