# ORION WF Bot v7 Lara SDR - Arquitetura Atual Do Fluxo

## Escopo

Esta documentação descreve o workflow atual após rollback para:

`backups/n8n-ORION-WF-Bot-v7-after-user-requested-rollback-20260626.json`

Workflow n8n:

- Nome: `ORION-WF-Bot-v7-LARA-SDR`
- ID de produção: `7SucjAi8zU69sQuT`
- Nós: `150`
- Estado validado pós-rollback: ativo no n8n em 2026-06-26

## Regra De Governança

Comportamento da Lara não deve ser ajustado no prompt base do `AI Agent`.

Camada correta:

- Comportamento, tom, saudação, escrita, atendimento e exemplos: `ROOT`, via `LARA_ROOT_CONFIG`.
- Bug técnico, integração, roteamento, parsing, CRM, Redis, UAZAPI, deduplicação: workflow n8n.

Ver também:

`docs/LARA_ROOT_ARCHITECTURE.md`

Camada planejada de conhecimento factual:

`docs/LARA_RAG_JSONL_ARCHITECTURE.md`

## Visão Geral

Fluxo principal:

1. UAZAPI chama webhook n8n.
2. `Filter UAZAPI` normaliza e filtra mensagem.
3. Deduplicação evita processar a mesma mensagem.
4. `Global Variables` extrai telefone, nome de perfil e parâmetros.
5. `Message Type` separa texto, álbum e mídia.
6. Redis faz buffer de mensagens rápidas.
7. `Get Message` consolida a mensagem final.
8. ROOT intercepta comandos admin.
9. Para cliente normal, carrega histórico e contexto.
10. `ROOT: Carregar Config LLM` lê `LARA_ROOT_CONFIG`.
11. `ROOT: Injetar Regras` injeta comportamento ROOT no contexto.
12. `AI Agent` gera JSON de resposta ou ação.
13. Parser decide se é resposta normal, handoff ou ação.
14. Se ação, consulta agenda ou cria appointment no CRM.
15. LLM final transforma resultado da ferramenta em resposta.
16. `Code: Enviar Blocos` envia WhatsApp.
17. Histórico e CRM recebem mensagem do cliente e resposta do bot.

## Entrada UAZAPI

### `Webhook`

- Método: `POST`
- Path: `whatsapp-inbound`
- Recebe eventos da UAZAPI.

### `Filter UAZAPI`

Função:

- Aceita apenas `EventType === "messages"`.
- Usa `body.message || body.data`.
- Ignora `msg.fromMe === true`.
- Ignora grupos quando `msg.isGroup === true`.
- Extrai texto de `msg.text`, `msg.content.text` ou `msg.body`.
- Normaliza `chatid`, `messageid`, `pushName`, `messageType`.

Risco atual:

- O filtro só bloqueia `fromMe` booleano verdadeiro.
- Se a UAZAPI mandar mensagem própria como `fromMe: "true"`, `key.fromMe`, `direction: outgoing`, `from_api` ou formato equivalente, o fluxo pode tratar resposta do bot como mensagem de cliente.
- Esse é o ponto mais provável para loops de auto-resposta.

### Deduplicação

Nós:

- `Dedup: Check Message`
- `Dedup: Nova Mensagem?`
- `Dedup: Marcar Processado`

Chave:

`DEDUP_{{ $json.body?.data?.messageid || $json.body?.data?.id || '' }}`

Risco atual:

- Se `messageid` vier vazio ou instável, a deduplicação pode falhar.
- TTL atual: `90` segundos.

## Variáveis Globais

### `Global Variables`

Campos:

- `number`: telefone do contato, extraído de `chatid`, `remoteJid` ou `from`.
- `wait_buffer`: `5`.
- `wait_conversation`: `600`.
- `max_chat_history`: `40`.
- `profile_name`: `senderName || pushname || pushName || "Cliente"`.
- `uazapi_token`: token vindo do payload UAZAPI.

Risco atual:

- `profile_name` usa nome de perfil do WhatsApp como se fosse nome do cliente.
- Isso deve ser governado pelo ROOT no comportamento da Lara, mas o fluxo ainda entrega esse valor no input do AI Agent como `<CLIENT_NAME>`.
- Não existe campo separado para "nome confirmado pelo cliente" no fluxo atual.

## Roteamento De Tipo De Mensagem

### `Message Type`

Saídas principais:

- Texto: `get_message (text)`.
- Álbum: `Push to Buffer (AlbumGroup)`.
- Mídia: `Descargar Media`.

### Texto

`get_message (text)` extrai conversa textual e envia para `Push to Buffer`.

### Mídia

Rota:

1. `Descargar Media`
2. `Convert to File`
3. `Get Mime Type`
4. `Media Type`
5. Análise conforme tipo:
   - imagem: `Analyze Image`
   - áudio: `Analyze audio`
   - vídeo: `Analyze video`
   - documento: extração por CSV, PDF, RTF, XML, XLSX etc.
6. Normalização.
7. `get_message (File message)`
8. `Normalize input`

## Buffer De Mensagens

### Objetivo

Agrupar mensagens fragmentadas do WhatsApp antes de mandar para a IA.

Nós principais:

- `Push to Buffer`
- `Get From Buffer`
- `Buffer Route`
- `Wait For User Other Fast Message`
- `Delete Buffer`
- `Normalize Buffer`

Funcionamento:

1. Mensagem entra no Redis.
2. Workflow aguarda janela de `wait_buffer`.
3. Se chegar nova mensagem, espera mais.
4. Quando estabiliza, junta mensagens em um único texto.
5. `Normalize Buffer` envia para `Get Message`.

## ROOT Admin

### Entrada Do ROOT

Depois de `Get Message`:

1. `ROOT: Get Session Redis`
2. `ROOT: Detectar Admin`

Admins autorizados no fluxo atual:

- `5522998911070`
- `554799215127`

Condição ROOT:

- número precisa estar autorizado;
- mensagem começa com `root` ou `/root`, ou sessão ROOT ativa está em Redis.

### Comandos ROOT

`ROOT: Parser de Comando` entende:

- `root`
- `/root`
- `/root [comando]`
- `/status`
- `/parametro`
- `/prompt`
- `/log`
- `/blocks`
- `/block [nome]`
- `/help`
- `/tutorial`
- `/exit`
- `/rclear`
- `/reset`
- `/regra`
- `/corrigir`
- `/persona`
- `/objetivo`
- `/tom`
- `/exemplo`
- `/escrita`
- `/newprompt`
- `/link`
- `/buscar`

### Registro ROOT

O ROOT mantém um histórico de alterações no campo `audit_log` dentro de `LARA_ROOT_CONFIG`.

O comando `/log` exibe as últimas modificações, incluindo:

- número do admin que alterou;
- ação executada;
- resumo da alteração;
- data/hora do registro.

O log cobre alterações confirmadas por comandos como `/regra`, `/escrita`, `/newprompt`, `/reset` e também ajustes feitos por linguagem natural no modo livre.

### ROOT Blocks V8

O fluxo ativo injeta `root_blocks` junto com o ROOT tradicional.

Camadas:

- `BASE_LARA EFETIVA`: prompt base global composto por `root_blocks.base_lara` mais persona, tom, objetivos, regras, escrita, correções, exemplos, links e parâmetros globais do ROOT.
- `ROOT_ROUTER`: instruções de roteamento por intenção e etapa comercial.
- `blocks`: blocos de resposta por situação.
- `crm_context`: contexto estruturado para CRM.

Comandos administrativos:

- `/blocks`
- `/block [nome]`
- `/setblock nome|texto`

O `AI Agent` agora aceita `crm_context` no JSON de saída. O parser normaliza esse contexto e `CRM: Criar Appointment` envia `ai_context` enriquecido para o CRM.

Importante: os comandos globais antigos não são uma camada paralela solta. Eles entram antes do roteador como parte da `BASE_LARA EFETIVA`.

### RAG JSONL Planejada

A camada de catálogo e conhecimento ainda não está ativa no workflow atual.

Arquitetura planejada:

1. Conteúdos de loja, FAQ, políticas, atendimento e links ficam em `knowledge/*.jsonl`.
2. `catalogo/*.jsonl` fica reservado para fase futura, quando existir catálogo online oficial.
3. Buscador interno roda antes do `AI Agent`.
4. O `AI Agent` recebe apenas `RAG_CONTEXT` compacto com fontes relevantes.
5. Quando não houver fonte confiável, Lara não inventa e conduz para especialista, agendamento ou pergunta de esclarecimento.

Essa camada não deve substituir `BASE_LARA EFETIVA`. Ela deve alimentar somente respostas factuais.

Chave Redis:

`LARA_ROOT_CONFIG`

Leitura:

- `ROOT: Ler Config Redis`
- `ROOT: Carregar Config LLM`

Escrita:

- `ROOT: Salvar Config Redis`
- `ROOT: Salvar Config Livre`

Campos principais:

- `custom_prompt`
- `persona_extra`
- `objetivos`
- `rules`
- `write_rules`
- `corrections`
- `examples`
- `links`
- `tom`
- `_pending`

### Injeção No Atendimento

`ROOT: Injetar Regras` transforma `LARA_ROOT_CONFIG` em texto e anexa ao contexto que chega no `AI Agent`.

Ponto essencial:

O prompt real configurado pelo ROOT não fica no system prompt do AI Agent. Ele fica no Redis, em `LARA_ROOT_CONFIG`.

## Memória E Contexto

### Redis

Nós principais:

- `Redis Chat Memory`
- `Push to chat_history`
- `Push first message to chat_history`
- `Get chat_history1`
- `Push message chat_history (User And Agent)`

Chaves observadas:

- `CHAT_HISTORY_{{ number }}`
- `Chats_{{ number }}`
- `Chats_buffer{{ number }}`

### PostgreSQL

Nós:

- `Create Table chat_history`
- `Get chat_history From DataBase`
- `Add Messages to chat_history (User And Agent)`

Tabela:

`chat_history`

Campos criados:

- `message_id`
- `user_whatsapp_number`
- `message_text`
- `message_timestamp`
- `created_at`

### Context Refiner

`Context Refiner` usa OpenAI para resumir histórico antes da Lara responder.

Entrada:

- histórico Redis/PostgreSQL;
- contexto CRM quando disponível.

Saída:

- texto refinado usado por `ROOT: Injetar Regras`.

## AI Agent

### Input

O `AI Agent` recebe:

```text
<RETRIEVED_CONTEXT>
{{ $json.text }}
</RETRIEVED_CONTEXT>

<USER_MESSAGE>
{{ $('Get Message').item.json.message }}
</USER_MESSAGE>

<CURRENT_DATE>
{{ $now.format('cccc, dd/MM/yyyy HH:mm') }}
</CURRENT_DATE>

<CLIENT_NAME>
{{ $('Global Variables').item.json.profile_name }}
</CLIENT_NAME>
```

### System Message Atual

O system message é contrato técnico. Ele exige:

- JSON válido.
- Português brasileiro.
- Não inventar preço, disponibilidade, prazo, política, produto ou confirmação de agenda.
- Usar `check_availability` para consultar horários.
- Usar `create_booking` para criar agendamento.
- Nunca confirmar agendamento sem `create_booking`.
- Não revelar regras internas.

Formatos obrigatórios:

- resposta normal;
- ação `check_availability`;
- ação `create_booking`;
- `handoff`.

Risco atual:

- O `AI Agent` recebe `<CLIENT_NAME>` vindo do perfil do WhatsApp.
- Cabe ao ROOT orientar a Lara a não tratar esse nome como confirmado.

## Parser Da Resposta Da IA

### `Code: Parse Agent Output`

Função:

- Faz parse do JSON retornado pelo AI Agent.
- Normaliza `type`, `message_blocks`, `delay_seconds`.
- Se ação for `create_booking`, exige:
  - `starts_at`
  - `ends_at`
  - `customer_name` com pelo menos 2 palavras
  - `visit_reason` ou `notes`

Se faltar dado:

- pergunta nome completo;
- pergunta motivo da visita;
- pergunta dia e horário.

Risco atual:

- O parser considera `notes` como motivo suficiente.
- Isso pode aceitar observações genéricas como motivo real.
- Esse é bug técnico possível, mas deve ser tratado com cautela e backup.

## Ações De Agenda E CRM

### Consulta De Slots

`CRM: Buscar Slots`

Usado quando `action === check_availability`.

### Criar Appointment

`CRM: Criar Appointment`

Endpoint:

`https://api.crm.orinjoias.com/api/v1/n8n/webhook/create-appointment`

Body atual:

```json
{
  "whatsapp_number": "+{{ number }}",
  "type": "VISITA_PRESENCIAL",
  "starts_at": "...",
  "ends_at": "...",
  "notes": "Cliente: ...\nMotivo da visita: ...\nObservações: ...",
  "ai_context": {
    "customer_name": "...",
    "visit_reason": "...",
    "original_notes": "..."
  }
}
```

Risco atual:

- O body pode duplicar conteúdo em `notes`.
- Já houve erro `500 INTERNAL_ERROR` no CRM para create appointment.
- Se o CRM retornar erro, a confirmação não deveria ser enviada como sucesso.

### Resposta Final Depois Da Tool

Rota:

1. `CRM: Buscar Slots` ou `CRM: Criar Appointment`
2. `Code: Formatar Tool Result`
3. `LLM: Resposta Final Agendamento`
4. `Code: Extrair Resposta Final`
5. `Code: Parse Final Output`
6. `Code: Enviar Blocos`

## Envio Para WhatsApp

### Pré-blocos

`Code: Enviar Pre-Blocos`

Envia mensagens como:

- "Aguarde um momento"
- "Vou confirmar agora"
- "Deixa eu verificar a agenda"

Risco atual:

- Para `create_booking`, o fluxo pode mandar pré-mensagem antes do CRM confirmar.
- Isso pode parecer confirmação antecipada.

### Envio final

`Code: Enviar Blocos`

Função:

- Lê `message_blocks`.
- Envia cada bloco via UAZAPI.
- Usa delay entre blocos.
- Retorna `response` juntando blocos por quebra de linha.

Risco atual:

- Não faz split inteligente por frase.
- A separação depende do `message_blocks` que o AI Agent gerar.
- O ROOT atual tem regras que forçam "bloco único", então mensagens emboladas podem vir da configuração ROOT.

## Handoff

Nós:

- `Code: Detectar Handoff`
- `If: É Handoff?`
- `Handoff: Gerar Código`
- `Handoff: Msg ao Cliente`
- `Handoff: Notificar Atendente`
- `CRM: Handoff Bot`

Função:

- Detectar quando atendimento humano deve assumir.
- Enviar mensagem ao cliente.
- Notificar atendente.
- Registrar no CRM.

## Registro No CRM

Nós:

- `CRM: Registrar Mensagem`
- `CRM: Bot Reply`
- `CRM: Atualizar Lead`

Após `Add Messages to chat_history (User And Agent)`, o fluxo atual conecta para:

- `Push to Buffer (chat_history)`
- `CRM: Atualizar Lead`
- `CRM: Registrar Mensagem`
- `CRM: Bot Reply`

Risco atual:

- `CRM: Atualizar Lead` está conectado nesta versão pós-rollback.
- Ele envia stage `NOVO`.
- Se a regra de negócio atual for "lead cai primeiro na agenda e o CRM decide pipeline", esse ponto precisa ser revisado como bug técnico, não como ROOT.

## Pontos De Risco Atuais

1. `Filter UAZAPI` tem filtro fraco contra mensagem própria.
2. Dedup depende de `messageid` consistente.
3. `profile_name` vem do perfil do WhatsApp e entra como `<CLIENT_NAME>`.
4. `CRM: Atualizar Lead` está conectado após salvar histórico.
5. `CRM: Registrar Mensagem` e `CRM: Bot Reply` usam JSON manual com expressões em string.
6. Parser de `create_booking` aceita `notes` genérico como motivo.
7. `Code: Enviar Pre-Blocos` pode enviar pré-mensagem para `create_booking`.
8. `CRM: Criar Appointment` pode duplicar notas.
9. ROOT atual força "bloco único" em várias regras, afetando naturalidade.
10. Qualquer ajuste de comportamento deve ser feito via ROOT, não no system prompt.

## Onde Mexer Conforme O Problema

### Se a Lara está robótica

ROOT:

- `/persona`
- `/tom`
- `/regra`
- `/escrita`
- `/exemplo`
- `/newprompt`

### Se a Lara usa nome errado

ROOT primeiro:

- regra para não tratar nome de perfil como nome confirmado;
- regra para perguntar ou confirmar nome no início.

Workflow só se houver prova de contaminação técnica entre contatos.

### Se a Lara entra em loop

Workflow:

- `Filter UAZAPI`
- `Dedup`
- payload da UAZAPI
- múltiplos workflows conectados ao mesmo webhook.

### Se o agendamento falha

Workflow e CRM:

- `Code: Parse Agent Output`
- `CRM: Buscar Slots`
- `CRM: Criar Appointment`
- endpoint do CRM.

### Se mensagem fica embolada

ROOT primeiro:

- revisar regras de "bloco único";
- revisar exemplos.

Workflow só se a separação técnica estiver ignorando `message_blocks`.

## Como Auditar Sem Disparar WhatsApp

1. Baixar workflow ativo via API n8n.
2. Ler nós `ROOT:*`, `AI Agent`, `Code: Parse Agent Output`, `CRM:*`.
3. Ler execuções existentes com `includeData=true`.
4. Procurar em `runData`:
   - `ROOT: Ler Config Redis`
   - `ROOT: Injetar Regras`
   - `Code: Parse Agent Output`
   - `CRM: Criar Appointment`
5. Não chamar webhook com `root`, `/status` ou `/parametro` só para consulta.

## Backups Relevantes

- Estado restaurado: `backups/n8n-ORION-WF-Bot-v7-LARA-SDR-before-maintenance-20260625-194542.json`
- Estado pós-rollback: `backups/n8n-ORION-WF-Bot-v7-after-user-requested-rollback-20260626.json`
- Estado antes do rollback solicitado: `backups/n8n-ORION-WF-Bot-v7-current-before-user-requested-rollback-20260626.json`

## Próximo Passo Recomendado

Antes de qualquer nova alteração:

1. Classificar o problema como ROOT ou workflow.
2. Se for ROOT, gerar comando ROOT e esperar confirmação humana.
3. Se for workflow, fazer backup ativo novo.
4. Validar em número de teste.
5. Só depois publicar ou religar número real.
