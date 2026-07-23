# Historico De Versoes - Lara V9

## Versao anterior preservada

Tag proposta/criada para preservar o estado anterior ao fechamento deste handoff:

```text
lara-v9-pre-rclear-20260723
```

Commit base:

```text
12702b7 Persist Lara session state in LangGraph
```

Esse ponto representa o estado antes da consolidacao final de README/handoff e antes de registrar formalmente as correcoes recentes de reset e confirmacao final.

Use essa tag quando precisar comparar o comportamento anterior ou restaurar a base antes das correcoes de conversa mais recentes.

## Versao atual de trabalho

Escopo da versao atual:

- LangGraph com estado persistido por `LARA_STATE_FILE`.
- Runtime `lara-langgraph` em container separado, acessivel pelo n8n na rede Docker.
- Workflow n8n V9 ativo como principal no momento da ultima verificacao.
- Correcao de confirmacao final de agendamento.
- Correcao de `/rclear` para limpar sessao no LangGraph.
- Correcao de saudacao duplicada apos reset.
- Telemetria honesta no envio de blocos WhatsApp.
- QA local e smoke remoto documentados.

## Alteracoes funcionais recentes

### Confirmacao final

Antes:

```text
Cliente: Sim e isso mesmo
Lara: interpretava como novo detalhe do atendimento.
```

Depois:

```text
Cliente: Sim e isso mesmo
Lara: reconhece como confirmacao final e gera create_appointment.
```

Execucao usada para diagnostico:

```text
4206
```

### Reset de conversa

Antes:

```text
/rclear
```

entrava como texto comum e podia ser gravado como detalhe/motivo do atendimento.

Depois:

```text
/rclear
```

gera:

```text
intent=session_clear
conversation_stage=inicio
collected_context={}
```

Execucoes usadas para diagnostico:

```text
4209
4210
4211
```

### Saudacao apos reset

Antes:

```text
Ola, tudo bem. Tudo bem?
```

Depois:

```text
Ola, tudo bem?
Aqui e a Lara, consultora virtual da ORIN Joias.
Para que eu consiga te oferecer um atendimento mais preciso, voce poderia me informar seu nome?
```

## Criterio Para Criar Nova Versao

Uma nova versao so deve ser marcada quando houver:

- commit no Git;
- teste local passando;
- health remoto do LangGraph OK;
- execution id do n8n analisada;
- resultado de WhatsApp real ou QA documentado;
- comentario no issue `ORION-CRM#14`.

## Rollback

Rollback de LangGraph:

```bash
git checkout lara-v9-pre-rclear-20260723 -- lara_langgraph Dockerfile.langgraph docker-compose.langgraph.yml tests/test_lara_langgraph.py
```

Depois reconstruir no VPS:

```bash
cd /docker/n8n-zcac/lara-src
docker build -f Dockerfile.langgraph -t n8n-zcac-lara-langgraph:latest .
cd /docker/n8n-zcac
docker compose up -d --no-deps --force-recreate lara-langgraph
```

Rollback de n8n:

- usar backups em `backups/`;
- validar workflow antes de ativar;
- confirmar que apenas uma workflow responde o numero de teste/producao.

Nao usar rollback para limpar conversa presa. Para isso, primeiro usar `/rclear` e verificar a memoria persistida.
