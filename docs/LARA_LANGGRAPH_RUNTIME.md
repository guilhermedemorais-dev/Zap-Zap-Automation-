# Lara LangGraph Runtime

## Decisão

O gargalo atual deixou de ser só ajuste de prompt. A Lara precisa de controle de estado fora do prompt livre.

Decisão aplicada neste repositório:

```text
n8n fica como shell de WhatsApp, ROOT, CRM e envio.
LangGraph vira runtime de decisão conversacional da Lara.
```

## O Que Foi Implementado

Arquivos:

- `lara_langgraph/graph.py`: grafo de estados da Lara.
- `lara_langgraph/service.py`: API FastAPI para o n8n chamar.
- `tests/test_lara_langgraph.py`: QA de jornadas críticas.
- `requirements-langgraph.txt`: dependências.
- `Dockerfile.langgraph`: imagem para hospedar o serviço.

Fonte técnica validada:

- `https://github.com/langchain-ai/langgraph.git`
- commit pesquisado localmente: `5931a5f`
- API confirmada: `StateGraph`, `START`, `END`, `add_conditional_edges`, `compile(checkpointer=...)`, `graph.invoke(..., {"configurable": {"thread_id": "..."}})`

Endpoint:

```http
POST /v1/lara/turn
```

Entrada:

```json
{
  "session_id": "wa:+5547999990000",
  "phone": "+5547999990000",
  "profile_name": "Nome do perfil, apenas informativo",
  "message": "Boa noite",
  "state": {},
  "available_slots": []
}
```

Importante:

- `session_id` vira `thread_id` do LangGraph.
- A memória curta usa checkpointer do LangGraph.
- `state` continua aceito por compatibilidade com o n8n atual, mas não deve ser a única fonte de memória em produção.

Saída:

```json
{
  "reply_blocks": [],
  "intent": "identification|discovery|appointment|catalog|closing",
  "conversation_stage": "identificacao|descoberta|agenda_slots|agenda_contexto|agenda_detalhes|agenda_tipo_joia|agenda_contato|agenda_resumo_confirmacao|agenda_criar|encerrado",
  "lead_temperature": "frio|morno|quente",
  "collected_context": {},
  "missing_fields": [],
  "next_action": "reply|check_availability|create_appointment",
  "tool_payload": {},
  "crm_note": "",
  "state": {},
  "safety": {
    "used_confirmed_facts_only": true,
    "needs_human": false
  }
}
```

## Estados Implementados

```mermaid
flowchart TD
  A["inicio"] --> B["identificacao"]
  B --> C["descoberta"]
  C --> D["agenda_slots"]
  D --> E["agenda_contexto"]
  E --> F["agenda_detalhes"]
  F --> G["agenda_tipo_joia"]
  G --> H["agenda_contato"]
  H --> I["agenda_resumo_confirmacao"]
  I --> J["agenda_criar"]
  C --> K["catalogo_info"]
  C --> L["encerrado"]
```

## Regras Críticas Implementadas

- Saudação não vira nome.
- Nome de perfil do WhatsApp não vira nome confirmado.
- Memória curta por `session_id` via checkpointer LangGraph.
- Depois que o cliente informa nome, a Lara vai para descoberta, não repete abertura.
- Erro de digitação simples em agendamento é entendido, como `qro agenda uma vizta`.
- Horário escolhido não cria appointment imediatamente.
- Antes de criar appointment, Lara coleta motivo da visita.
- Antes de pedir e-mail, Lara coleta contexto consultivo da compra.
- Antes de pedir e-mail, Lara identifica se o cliente quer joia pronta ou personalizada.
- E-mail e confirmação do WhatsApp são coletados antes do resumo final.
- Antes de criar appointment, Lara resume e pede confirmação.
- Se o cliente corrigir o resumo, Lara atualiza o contexto e confirma novamente.
- Endereço fixo correto:
  - `Av. Brasil, 1500 - Centro, Balneário Camboriú - SC, 88330-901`

## Como Rodar Local

```bash
python3 -m venv .venv-langgraph
. .venv-langgraph/bin/activate
pip install -r requirements-langgraph.txt
uvicorn lara_langgraph.service:app --host 0.0.0.0 --port 8080
```

Health check:

```bash
curl http://127.0.0.1:8080/health
```

Exemplo:

```bash
curl -s http://127.0.0.1:8080/v1/lara/turn \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"wa:+5547999990000","phone":"+5547999990000","message":"Boa noite","state":{}}'
```

## Como O n8n Deve Integrar

O fluxo remoto não deve tentar rodar LangGraph dentro de Code node.

Integração correta:

```mermaid
flowchart TD
  A["n8n: WhatsApp inbound"] --> B["Filtro anti-loop + dedup"]
  B --> C["Carregar ROOT e sessão"]
  C --> D["HTTP: Lara LangGraph /v1/lara/turn"]
  D --> E{"next_action"}
  E -->|reply| F["Enviar blocos WhatsApp"]
  E -->|check_availability| G["CRM: Buscar Slots"]
  G --> H["Chamar LangGraph novamente com available_slots"]
  H --> F
  E -->|create_appointment| I["CRM: Criar Appointment"]
  I --> J["Confirmar envio e salvar contexto"]
```

O n8n continua responsável por:

- receber webhook;
- bloquear mensagem própria;
- deduplicar;
- carregar ROOT;
- buscar slots;
- criar appointment;
- enviar WhatsApp;
- salvar histórico.

LangGraph fica responsável por:

- decidir estado;
- capturar nome confirmado;
- capturar motivo;
- capturar detalhes consultivos da visita;
- capturar preferência entre joia pronta e personalizada;
- capturar e-mail e confirmação do WhatsApp antes do CRM;
- montar resposta em blocos;
- decidir próxima ação;
- gerar `crm_note`.

## Memória

A versão local usa `InMemorySaver`, suficiente para QA e smoke local.

Para produção, isso ainda não é suficiente:

- `InMemorySaver` perde estado quando o serviço reinicia;
- produção deve usar checkpointer durável, preferencialmente Postgres;
- o `thread_id` deve ser derivado do número/conversa e nunca gerado pela IA.

## Bloqueio Operacional Atual

Para aplicar isso no n8n remoto, falta uma URL pública ou interna acessível pelo n8n para o serviço LangGraph.

Sem isso, qualquer alteração remota seria gambiarra:

- n8n remoto não consegue chamar `localhost` da máquina local;
- Code node do n8n não roda pacote Python `langgraph`;
- publicar um HTTP Request para URL inexistente quebraria produção.

## Próximo Passo Real

Escolher onde hospedar:

- no mesmo VPS do n8n, via Docker;
- no servidor do CRM;
- em um serviço externo com URL HTTPS.

Depois disso:

1. configurar `LARA_LANGGRAPH_URL`;
2. criar node HTTP `Lara LangGraph Turn`;
3. preservar fallback para o fluxo atual enquanto valida;
4. rodar QA remoto em número de teste;
5. só então ativar produção.
