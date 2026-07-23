# Auditoria n8n Para QA Simulator

## Resumo

Auditoria feita antes de qualquer alteração no workflow ativo.

Workflow:

- Nome: `ORION-WF-Bot-v7-LARA-SDR`
- ID: `7SucjAi8zU69sQuT`
- Ativo: `true`
- Nós: `150`
- Backup local: `backups/n8n-ORION-WF-Bot-v7-before-qa-simulator-20260630.json`

## Objetivo Da Auditoria

Identificar onde o `qa_mode` precisa bloquear efeitos colaterais antes de implementar o simulador.

Efeitos colaterais proibidos em QA:

- envio WhatsApp;
- criação de appointment;
- update de lead;
- registro de mensagem real no CRM;
- notificação de atendente;
- gravação em histórico real do cliente.

## Nós Críticos De Envio WhatsApp

| Nó | Tipo | Risco |
|---|---|---|
| `Code: Enviar Pre-Blocos` | Code | Envia mensagens preliminares pela UAZAPI antes das actions |
| `Code: Enviar Blocos` | Code | Envia `message_blocks` pela UAZAPI |
| `Handoff: Msg ao Cliente` | HTTP Request | Envia mensagem de handoff para cliente |
| `ROOT: Enviar Resposta Admin` | HTTP Request | Envia resposta ROOT para admin |
| `ROOT: Enviar Resposta Livre` | HTTP Request | Envia resposta do modo livre ROOT |
| `Send Response` | HTTP Request | Envia resposta por UAZAPI em rota antiga/auxiliar |

Regra P0:

```text
qa_mode nunca pode alcançar esses nós.
```

## Nós Críticos De CRM

| Nó | Tipo | Risco |
|---|---|---|
| `CRM: Buscar Slots` | HTTP Request | Consulta agenda real |
| `CRM: Criar Appointment` | HTTP Request | Cria appointment real |
| `CRM: Registrar Mensagem` | HTTP Request | Registra mensagem real |
| `CRM: Bot Reply` | HTTP Request | Registra resposta do bot |
| `CRM: Atualizar Lead` | HTTP Request | Pode mover/alterar lead |
| `CRM: Handoff Bot` | HTTP Request | Registra handoff real |
| `CRM: Lead Context` | HTTP Request | Busca contexto real do lead |

Regra P0:

```text
qa_mode deve usar mock para slots, booking e handoff.
qa_mode nao deve criar/update nada no CRM real.
```

## Nós De Decisão E Parser

| Nó | Função |
|---|---|
| `AI Agent` | Gera resposta ou action |
| `Code: Parse Agent Output` | Normaliza JSON do Agent |
| `If: É Action?` | Separa action de resposta |
| `Code: Formatar Tool Result` | Monta contexto pós-ferramenta |
| `LLM: Resposta Final Agendamento` | Gera resposta final depois da ferramenta |

Ponto de inserção recomendado:

```text
Code: Parse Agent Output
→ IF qa_mode?
  → sim: QA Router / mocks / output capture
  → não: fluxo atual normal
```

Observação importante:

- `If: É Action?` hoje envia action para `Code: Enviar Pre-Blocos`.
- Isso significa que o `qa_mode` deve interceptar antes de `Code: Enviar Pre-Blocos`.
- Se interceptar depois, o fluxo pode mandar mensagem real no WhatsApp.

## ROOT E Configuração

Nós relevantes:

- `ROOT: Carregar Config LLM`
- `ROOT: Injetar Regras`
- `ROOT: Parser de Comando`
- `ROOT: Processar Comando`
- `ROOT: Salvar Config Redis`

Regra:

- QA pode carregar ROOT;
- QA não deve salvar alteração ROOT automaticamente;
- QA não deve disparar resposta admin via WhatsApp.

## Memória E Redis

Nós relevantes:

- `Redis Chat Memory`
- `Push to chat_history`
- `Push first message to chat_history`
- `Get chat_history1`
- `Push message chat_history (User And Agent)`
- buffers Redis de mensagens.

Regra para QA:

```text
usar chave fake isolada por scenario_id.
prefixo sugerido: QA_LARA_{{ scenario_id }}_{{ fake_number }}
```

Não usar número real.

## Estratégia Segura Para QA Simulator

### Entrada

Criar entrada interna/manual com:

```json
{
  "qa_mode": true,
  "scenario_id": "QA-01",
  "fake_number": "+550000000001",
  "message": "Olá"
}
```

### Interceptação

Inserir IF logo depois de `Code: Parse Agent Output`:

```text
if qa_mode == true
→ QA: Normalizar Output
→ QA: Mock Action se precisar
→ QA: Capturar Resultado
else
→ If: É Action? atual
```

### Mocks

- `check_availability`: retorna horários fixos.
- `create_booking`: retorna appointment simulado.
- `handoff`: retorna handoff simulado.

### Saída

Gerar item compatível com:

`qa/lara_actual_outputs.json`

## Critérios Para Considerar LARA-003 Concluída

- backup criado;
- nós críticos identificados;
- ponto seguro de interceptação definido;
- regra P0 de bloqueio de side effects documentada;
- próxima tarefa liberada: `LARA-004`.

Status: concluída localmente.
