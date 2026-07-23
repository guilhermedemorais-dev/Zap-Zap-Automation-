# ORIN Joias - Lara V9 WhatsApp SDR

## Resumo

Este repositorio documenta e versiona a automacao Lara V9 da ORIN Joias.

A Lara atende clientes pelo WhatsApp, qualifica a intencao, conduz o agendamento presencial, consulta horarios reais no CRM, cria appointment no CRM e envia o endereco correto somente depois da confirmacao do agendamento.

O objetivo principal desta versao e reduzir alucinacao e loop de atendimento separando responsabilidades:

- n8n orquestra WhatsApp, ROOT, CRM, envio e historico;
- LangGraph controla estado conversacional, memoria curta e decisao da proxima etapa;
- CRM e a fonte de verdade para horarios e agendamentos;
- ROOT e console/admin para comportamento e parametros da Lara, nao o motor principal de estado.

## Estado Atual

Branch de trabalho:

```text
codex/lara-v9-shadow-readiness
```

Workflow n8n atual:

```text
LARA V9 Shadow SDR
id: 7kXu17NYpsN8Yc65
```

Workflow antigo de referencia:

```text
ORION-WF-Bot-v7-LARA-SDR
id: 7SucjAi8zU69sQuT
```

LangGraph interno:

```text
http://lara-langgraph:8080/v1/lara/turn
health: http://lara-langgraph:8080/health
```

CRM agenda:

```text
Agenda primeiro, pipeline depois.
O agendamento precisa preencher nome, WhatsApp, data, horario, motivo e observacoes.
```

Endereco oficial:

```text
Av. Brasil, 1500 - Centro, Balneario Camboriu - SC, 88330-901
Google Maps: https://maps.app.goo.gl/geMC3hHsQqGfSnnm6
```

## Arquitetura Ponta A Ponta

```mermaid
flowchart TD
  A["Cliente no WhatsApp"] --> B["UAZAPI / webhook n8n"]
  B --> C["Filtro anti-loop e deduplicacao"]
  C --> D["Extracao de numero, texto, profile_name e qa_mode"]
  D --> E{"Admin ROOT?"}
  E -->|sim| F["ROOT console: status, comandos, config e logs"]
  E -->|nao| G["HTTP: Lara LangGraph Turn"]
  G --> H{"next_action"}
  H -->|reply| I["Enviar blocos no WhatsApp"]
  H -->|check_availability| J["CRM: buscar horarios reais"]
  J --> K["Normalizar slots para LangGraph"]
  K --> G
  H -->|create_appointment| L["CRM: criar appointment"]
  L --> M["Confirmacao + endereco + Maps"]
  M --> I
  H -->|handoff| N["Avisar instabilidade ou atendimento humano"]
  N --> I
```

## Responsabilidades Por Camada

### WhatsApp / UAZAPI

Responsavel por entregar mensagens recebidas e enviar blocos de resposta.

Regras:

- nunca processar mensagem enviada pelo proprio bot como se fosse cliente;
- preservar o numero real do cliente;
- separar mensagens em blocos curtos, como conversa humana;
- registrar erro de envio com telemetria honesta.

Telemetria esperada em envio:

```text
blocks_attempted
blocks_sent
send_success
send_errors
uazapi_token_present
```

### n8n

Responsavel por orquestrar o fluxo.

Faz:

- recebe webhook;
- detecta ROOT/admin;
- chama LangGraph;
- interpreta `next_action`;
- busca slots no CRM;
- cria appointment no CRM;
- envia mensagens WhatsApp;
- bloqueia side effects em `qa_mode`;
- guarda evidencias de execucao.

Nao deve fazer:

- decidir estado de conversa em prompt livre;
- inventar horario;
- confirmar appointment antes do CRM;
- guardar token em Set node ou texto puro;
- deixar dois workflows ativos respondendo o mesmo numero.

### LangGraph

Responsavel por estado e decisao conversacional.

Faz:

- isola memoria por `session_id`;
- confirma nome apenas quando o cliente informa;
- entende erro simples de digitacao;
- decide entre responder, buscar horario, criar appointment ou handoff;
- coleta motivo, detalhes, preferencia, e-mail e confirmacao do WhatsApp;
- monta `crm_note`;
- limpa sessao com `/rclear`.

Nao deve fazer:

- consultar CRM diretamente;
- enviar WhatsApp;
- usar nome do perfil como nome confirmado;
- inventar preco, estoque, produto ou horario;
- gravar saudacao, comando ou confirmacao curta como nome/motivo.

### CRM

Fonte de verdade para agenda.

Faz:

- retorna horarios disponiveis;
- cria appointment;
- registra lead/dados do cliente;
- alimenta a agenda visual e depois o pipeline de atendimento.

## Estados Conversacionais

Estados principais:

```text
inicio
identificacao
descoberta
agenda_slots
agenda_contexto
agenda_detalhes
agenda_tipo_joia
agenda_contato
agenda_resumo_confirmacao
agenda_criar
catalogo_info
encerrado
handoff
```

Fluxo feliz de agendamento:

```mermaid
sequenceDiagram
  participant C as Cliente
  participant W as WhatsApp/n8n
  participant L as LangGraph
  participant R as CRM

  C->>W: Boa noite
  W->>L: message=Boa noite
  L-->>W: Apresentacao + pergunta nome
  W-->>C: Blocos de resposta

  C->>W: Guilherme
  W->>L: message=Guilherme
  L-->>W: Pergunta interesse / catalogo ou agenda
  W-->>C: Blocos de resposta

  C->>W: Quero agendar atendimento presencial
  W->>L: message=Quero agendar...
  L-->>W: next_action=check_availability
  W->>R: Buscar slots reais
  R-->>W: slots
  W->>L: available_slots
  L-->>W: Lista horarios
  W-->>C: Horarios disponiveis

  C->>W: Pode ser as dez
  W->>L: message=Pode ser as dez
  L-->>W: Pede motivo da visita
  W-->>C: Pergunta motivo

  C->>W: Quero ver aliancas de casamento
  W->>L: motivo
  L-->>W: Pede detalhes/preferencia
  W-->>C: Perguntas consultivas

  C->>W: Meu email e...
  W->>L: dados contato
  L-->>W: Resumo e pedido de confirmacao
  W-->>C: Confirma para mim?

  C->>W: Sim, e isso mesmo
  W->>L: confirmacao final
  L-->>W: next_action=create_appointment
  W->>R: Criar appointment
  R-->>W: accepted=true
  W-->>C: Agendamento confirmado + endereco + Maps
```

## Contrato Da API LangGraph

Endpoint:

```http
POST /v1/lara/turn
```

Entrada minima:

```json
{
  "session_id": "wa:+5547999990000",
  "phone": "+5547999990000",
  "profile_name": "Nome do perfil, apenas informativo",
  "message": "Boa noite",
  "qa_mode": false,
  "state": {},
  "available_slots": []
}
```

Saida esperada:

```json
{
  "reply_blocks": [],
  "intent": "identification",
  "conversation_stage": "identificacao",
  "lead_temperature": "morno",
  "collected_context": {},
  "missing_fields": [],
  "next_action": "reply",
  "tool_payload": {},
  "crm_note": "",
  "state": {},
  "safety": {
    "used_confirmed_facts_only": true,
    "needs_human": false
  },
  "side_effects": {
    "send_whatsapp": true,
    "create_appointment": false,
    "update_crm": false
  }
}
```

Valores importantes de `next_action`:

```text
reply
check_availability
create_appointment
handoff
none
```

## Comandos Operacionais

### Limpar conversa do cliente

```text
/rclear
```

Comportamento esperado:

```text
Conversa reiniciada. Pode me chamar de novo quando quiser.
```

Depois disso, `Ola` precisa reiniciar em `identificacao`, sem contexto antigo.

### ROOT

ROOT e console/admin. Ele serve para diagnostico e ajustes de comportamento, mas nao deve substituir o controle de estado do LangGraph.

Comandos existentes/documentados:

```text
/status
/parametro
/persona [texto]
/tom [0-10]
/objetivo [texto]
/regra [texto]
/escrita [texto]
/corrigir [texto]
/exemplo entrada:X|saida:Y
/link nome|url|descricao
/newprompt [texto]
/clear
/reset
/exit
```

Regra de seguranca:

```text
Bug tecnico corrige no workflow/LangGraph.
Comportamento editorial corrige no ROOT.
```

## Como Rodar Localmente

```bash
python3 -m venv .venv-langgraph
. .venv-langgraph/bin/activate
pip install -r requirements-langgraph.txt
uvicorn lara_langgraph.service:app --host 0.0.0.0 --port 8080
```

Health:

```bash
curl http://127.0.0.1:8080/health
```

Turno de teste:

```bash
curl -s http://127.0.0.1:8080/v1/lara/turn \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"wa:+550000000001","phone":"+550000000001","message":"Boa noite","state":{}}'
```

## Como Rodar Testes

```bash
.venv-langgraph/bin/python -m unittest tests/test_lara_langgraph.py tests/test_lara_service.py -v
```

QA n8n:

```bash
.venv-langgraph/bin/python scripts/lara_n8n_qa_journey.py --delay 14
```

Validacao de sintaxe antes de commit:

```bash
git diff --check
```

## Deploy No VPS

O servico `lara-langgraph` roda como container separado, na mesma rede do n8n.

Comando de health a partir do container n8n:

```bash
docker exec n8n-zcac-n8n-1 wget -qO- http://lara-langgraph:8080/health
```

Rebuild/recreate do LangGraph:

```bash
cd /docker/n8n-zcac/lara-src
docker build -f Dockerfile.langgraph -t n8n-zcac-lara-langgraph:latest .
cd /docker/n8n-zcac
docker compose up -d --no-deps --force-recreate lara-langgraph
```

## Versoes E Rollback

Historico detalhado:

```text
docs/VERSION_HISTORY.md
```

Tag recomendada para estado anterior a este handoff:

```text
lara-v9-pre-rclear-20260723
```

Rollback operacional recomendado:

1. Identificar a causa da falha pela execution id do n8n.
2. Se for LangGraph, voltar imagem/container para o commit/tag anterior.
3. Se for workflow n8n, restaurar backup em `backups/`.
4. Validar health do LangGraph.
5. Rodar conversa de smoke no WhatsApp.

Nao fazer rollback cego se o problema for apenas estado contaminado. Primeiro testar `/rclear` e conferir o arquivo de estado persistido.

## Evidencias Importantes

Relatorio principal:

```text
qa/lara_v9_goal_report_20260720.md
```

Execucoes citadas:

```text
4206 - confirmacao final "Sim e isso mesmo" tratada errado antes do patch
4209 - memoria antiga contaminou nova mensagem
4210 - contexto antigo ainda preso
4211 - /rclear entrou como texto comum antes da correcao
```

Smoke remoto validado depois do patch:

```text
/rclear -> intent=session_clear, conversation_stage=inicio
Ola     -> intent=identification, conversation_stage=identificacao
```

## Pendencias Antes De Declarar 100%

Ainda falta teste real do usuario no WhatsApp depois da ultima correcao.

Checklist minimo:

- enviar `/rclear`;
- confirmar resposta de reset;
- iniciar com `Ola`;
- informar nome;
- pedir agendamento presencial;
- receber horarios reais do CRM;
- escolher horario;
- informar motivo da visita;
- informar detalhes;
- informar e-mail;
- confirmar WhatsApp;
- confirmar resumo;
- verificar appointment criado no CRM;
- verificar endereco correto enviado apenas no final.

QA de erro humano:

```text
Oii
Boa noite
qro agenda uma vizta
atendimento na loja
pode ser as dez
sim e isso mesmo
onde fica a loja?
quero falar com atendente
nao entendi
```

## Regra Para O Proximo Dev

Nao mexa no prompt primeiro.

Ordem correta de diagnostico:

1. Capturar execution id do n8n.
2. Abrir os nos:
   - `Get Message`
   - `ROOT: Detectar Admin`
   - `ROOT: Parser de Comando`
   - `Lara LangGraph Turn`
   - `Code: Parse Agent Output`
   - `Code: Enviar Blocos`
   - CRM slots/create appointment, se aplicavel.
3. Identificar onde quebrou.
4. Corrigir uma causa por rodada.
5. Adicionar teste local quando a falha for do LangGraph.
6. Validar n8n se tocar no workflow.
7. Registrar execution id e resultado no issue `ORION-CRM#14`.

Sem execution id ou evidencia real, nao declarar a automacao pronta.

## Mapa Completo Para Handoff

O mapa completo do fluxo esta em:

```text
docs/LARA_FULL_FLOW_MAP.md
```

Esse arquivo documenta:

- entrada WhatsApp/UAZAPI;
- deduplicacao e anti-loop;
- tratamento de texto;
- tratamento de audio, imagem, video e documentos;
- extracao de CSV, PDF, XLSX, JSON, XML, HTML, RTF, ICS e texto;
- buffer de mensagens;
- ROOT console;
- LangGraph;
- memoria persistida;
- CRM;
- envio WhatsApp;
- QA mode;
- scripts;
- knowledge/catalogo;
- backups;
- diagnostico por execution id;
- erros reais ja corrigidos;
- criterio de pronto.

## Prompt De Meta Para O Proximo Executor

Copie este prompt para a meta/tarefa do proximo agente executor:

```text
Voce vai assumir a tarefa ORION-CRM#14, Lara V9 WhatsApp SDR da ORIN Joias.

Sua responsabilidade e concluir e validar a automacao sem quebrar o que ja foi feito.

Antes de qualquer alteracao, leia obrigatoriamente:
1. README.md
2. docs/LARA_FULL_FLOW_MAP.md
3. docs/LARA_LANGGRAPH_RUNTIME.md
4. docs/VERSION_HISTORY.md
5. docs/LARA_V9_PRODUCTION_HANDOFF.md
6. qa/lara_v9_goal_report_20260720.md
7. docs/prompts/LARA_V9_EXECUTION_LOOP_PROMPT.md
8. lara_langgraph/graph.py
9. lara_langgraph/service.py
10. tests/test_lara_langgraph.py

Contexto:
- Workflow n8n atual: LARA V9 Shadow SDR, id 7kXu17NYpsN8Yc65.
- Workflow antigo de referencia: ORION-WF-Bot-v7-LARA-SDR, id 7SucjAi8zU69sQuT.
- LangGraph interno: http://lara-langgraph:8080/v1/lara/turn.
- Health: http://lara-langgraph:8080/health.
- Endereco correto: Av. Brasil, 1500 - Centro, Balneario Camboriu - SC, 88330-901.
- Maps correto: https://maps.app.goo.gl/geMC3hHsQqGfSnnm6.

O fluxo faz ponta a ponta:
1. Recebe mensagem do WhatsApp pela UAZAPI.
2. Filtra mensagem propria e deduplica por id.
3. Identifica se e texto, audio, imagem, video ou arquivo.
4. Para texto, normaliza e envia para buffer.
5. Para audio, baixa midia, transcreve e transforma em texto.
6. Para imagem, baixa midia, analisa imagem/caption e transforma em texto.
7. Para documentos, extrai CSV, PDF, XLSX, JSON, XML, HTML, RTF, ICS ou texto quando possivel.
8. Junta mensagens rapidas em buffer para evitar resposta fora de ordem.
9. Decide se a mensagem e ROOT/admin ou cliente.
10. ROOT administra status/configuracoes sem virar motor de estado.
11. Cliente segue para LangGraph.
12. LangGraph controla estado, memoria, nome confirmado, descoberta, agendamento, motivo, detalhes, contato, resumo e confirmacao.
13. Se precisar horario, LangGraph retorna check_availability.
14. n8n consulta slots reais no CRM.
15. n8n devolve slots ao LangGraph.
16. Lara apresenta horarios reais.
17. Cliente escolhe horario.
18. Lara coleta motivo, contexto e preferencia.
19. Lara coleta e-mail e confirma WhatsApp quando necessario.
20. Lara resume e pede confirmacao final.
21. Somente apos confirmacao final, LangGraph retorna create_appointment.
22. n8n cria appointment real no CRM.
23. n8n envia confirmacao, endereco correto e link do Google Maps.
24. n8n registra telemetria de envio.

Regras obrigatorias:
- Nao mexa em prompt primeiro. Diagnostique por execution id.
- Nao invente horario, endereco, preco, estoque ou link de produto.
- Nao use profile_name como nome confirmado.
- Nao pergunte nome de novo depois que o cliente informou.
- Nao crie appointment antes de motivo, contato e confirmacao final.
- Nao envie endereco antes do cliente pedir ou antes do agendamento confirmado.
- Nao deixe dois workflows responderem o mesmo numero.
- Nao rode QA com side effects reais.
- Nao commite dumps brutos sem scan de segredo.

Primeira acao:
1. Rode git status.
2. Confirme workflows ativos no n8n.
3. Rode health do LangGraph de dentro do container n8n.
4. Peça ou capture uma execution id do erro mais recente.
5. Abra os nos Get Message, ROOT, Lara LangGraph Turn, Parse Agent Output, Enviar Blocos e CRM.
6. Corrija uma causa por rodada.
7. Adicione teste local se tocar no LangGraph.
8. Registre evidencias no issue ORION-CRM#14.

Criterio de conclusao:
So declare READY quando a jornada real WhatsApp -> n8n -> LangGraph -> CRM slots -> LangGraph -> CRM appointment -> WhatsApp passar, com appointment visivel no CRM e execution id registrada.
```
