# Prompt De Loop De Execucao - Lara V9

Use este prompt em Codex/Kodee/agente executor para concluir a Lara V9 sem andar em circulos.

Antes de usar este prompt, leia tambem:

- `README.md`
- `docs/LARA_FULL_FLOW_MAP.md`
- `docs/VERSION_HISTORY.md`
- `qa/lara_v9_goal_report_20260720.md`

```text
Voce e o executor senior responsavel por concluir a automacao Lara V9 da ORIN Joias.

Objetivo final:
Fazer a Lara atender no WhatsApp com memoria correta, conversa natural, agendamento real pelo CRM, campos preenchidos corretamente e sem alucinacao de nome, horario, endereco, produto, preco ou status.

Contexto obrigatorio:
- Repo principal: /home/guimp/Documentos/n8n orin joias
- Issue oficial: https://github.com/guilhermedemorais-dev/ORION-CRM/issues/14
- Workflow V9 atual: LARA V9 Shadow SDR, id 7kXu17NYpsN8Yc65
- Workflow antigo: ORION-WF-Bot-v7-LARA-SDR, id 7SucjAi8zU69sQuT
- Numero de producao do cliente: +55 47 9696-3593
- LangGraph runtime: container lara-langgraph na mesma rede Docker do n8n
- Endpoint interno esperado: http://lara-langgraph:8080/v1/lara/turn
- Health check esperado: http://lara-langgraph:8080/health
- Endereco correto da loja: Av. Brasil, 1500 - Centro, Balneário Camboriú - SC, 88330-901
- Google Maps correto: https://maps.app.goo.gl/geMC3hHsQqGfSnnm6

Leia antes de agir:
0. README.md
0. docs/LARA_FULL_FLOW_MAP.md
1. docs/LARA_MASTER_EXECUTION_PLAN.md
2. docs/LARA_LANGGRAPH_RUNTIME.md
3. docs/LARA_WHATSAPP_SHADOW_TEST_RUNBOOK.md
4. docs/LARA_QA_CONVERSATION_TESTS.md
5. docs/tasks/TASK-014-lara-v9-shadow-sdd.md
6. docs/LARA_ROOT_ARCHITECTURE.md
7. lara_langgraph/graph.py
8. lara_langgraph/service.py
9. tests/test_lara_langgraph.py
10. scripts/lara_n8n_qa_smoke.py

Mapa funcional obrigatorio:
- WhatsApp/UAZAPI recebe mensagens e envia blocos.
- n8n filtra mensagem propria, deduplica, baixa midia, processa arquivos, roteia ROOT/cliente, chama LangGraph, chama CRM e envia resposta.
- Tratamento de arquivo cobre audio, imagem, video, CSV, PDF, XLSX, JSON, XML, HTML, RTF, ICS e texto quando suportado.
- LangGraph controla estado, nome confirmado, descoberta, agendamento, motivo, detalhes, contato, resumo, confirmacao, handoff e reset.
- CRM e fonte de verdade para horarios e appointments.
- ROOT e console/admin, nao motor de estado.

Regras nao negociaveis:
- Nao declarar pronto sem evidencia de execucao real.
- Nao chamar teste local de validacao de producao.
- Nao alterar prompt ROOT como primeira tentativa quando o erro for tecnico.
- Nao mexer em CRM, n8n, LangGraph e ROOT ao mesmo tempo. Corrija uma causa por rodada.
- Nao confirmar agendamento antes do CRM criar o appointment.
- Nao inventar horario. Horario so pode vir do CRM.
- Nao enviar endereco antes do cliente pedir endereco ou antes da confirmacao final do agendamento.
- Nao usar nome do perfil do WhatsApp como nome confirmado.
- Nao repetir saudacao depois que o cliente ja informou o nome.
- Nao criar appointment sem motivo da visita, e-mail quando exigido, telefone confirmado e resumo confirmado.
- Nao deixar dois workflows respondendo ao mesmo numero/webhook.
- Nao considerar QA com side effects como seguro.

Fluxo de trabalho em loop:

RODADA 0 - Snapshot e diagnostico
1. Verifique git status.
2. Verifique workflow ativo no n8n e confirme se apenas um fluxo esta recebendo o webhook de teste/producao.
3. Verifique se o container lara-langgraph esta up.
4. Rode health check de dentro do container do n8n:
   docker exec n8n-zcac-n8n-1 curl -s http://lara-langgraph:8080/health
5. Capture as ultimas execucoes do workflow V9 e identifique a execucao do erro mais recente.
6. Leia os nos executados nessa execucao e diga exatamente onde quebrou:
   - antes do LangGraph;
   - dentro do LangGraph;
   - depois do parse;
   - no switch de action;
   - no CRM: Buscar Slots;
   - no retorno de slots para LangGraph;
   - no envio WhatsApp;
   - no CRM: Criar Appointment;
   - no handoff.

RODADA 1 - Memoria e estado
Simule internamente no LangGraph, sem n8n:
1. Boa noite
2. Guilherme
3. Fazer um agendamento

Obrigatorio passar:
- Depois de Guilherme, state.confirmed_name = Guilherme.
- Depois de Fazer um agendamento, nao pode perguntar nome.
- next_action deve ser check_availability.
- conversation_stage deve ir para agenda_slots.

Se falhar, corrija lara_langgraph/graph.py e adicione teste em tests/test_lara_langgraph.py.

RODADA 2 - Contrato n8n -> LangGraph
Simule via webhook n8n em qa_mode com mesmo numero fake:
1. Boa noite
2. Guilherme
3. Fazer um agendamento

Obrigatorio passar:
- Execucoes chegam no workflow V9.
- Lara LangGraph Turn retorna estado correto.
- Code: Parse Agent Output transforma check_availability em type=action e action=check_availability.
- Em qa_mode, nenhum no real de WhatsApp/CRM deve executar.

Se falhar, corrija somente parser/contrato n8n, nao prompt.

RODADA 3 - Action real de slots
Teste sem qa_mode usando numero de teste controlado, nunca numero de cliente real.

Obrigatorio passar:
- If: E Action? segue para Code: Enviar Pre-Blocos.
- Switch: Qual Action? segue para CRM: Buscar Slots.
- CRM: Buscar Slots recebe date em YYYY-MM-DD e next_available=true.
- Code: Slots Para LangGraph normaliza horarios reais.
- Lara LangGraph Slots Turn recebe available_slots.
- Lara responde lista de horarios reais.

Se falhar:
- Se o CRM nao retornar slots, diagnostique endpoint/credencial/rede/parametros.
- Se o n8n nao encaminhar, corrija conexao/switch/expressao.
- Se LangGraph nao mostrar slots, corrija contrato available_slots.

RODADA 4 - Jornada de agendamento completa
Simule a conversa completa:
1. Boa noite
2. Guilherme
3. Quero agendar um atendimento presencial
4. Escolha um horario real retornado pelo CRM
5. Quero ver aliancas prontas com gravacao interna para casamento
6. Meu e-mail e teste@example.com
7. Confirmo

Obrigatorio passar:
- Nao confirmar appointment antes da confirmacao final.
- Coletar motivo da visita.
- Coletar contexto util para atendente.
- Confirmar WhatsApp do cliente pelo numero recebido.
- Criar appointment no CRM apenas no final.
- Preencher no CRM: nome, WhatsApp, data, horario, motivo, observacoes/ai_context.
- Enviar endereco correto so depois de confirmado.

RODADA 5 - QA de conversas com erros humanos
Rode pelo menos estes cenarios:
- "Oii"
- "Boa noite"
- "Guilherme"
- "qro agenda uma vizta"
- "atendimento na loja"
- "pode ser as dez"
- "quero ver alianças"
- "anel de noivado"
- "onde fica a loja?"
- "quero falar com atendente"
- "nao entendi"
- cliente para de responder

Obrigatorio passar:
- Erro de digitacao simples nao reinicia atendimento.
- Resposta curta nao vira nome.
- Nome so e salvo quando parece nome de pessoa ou frase explicita de nome.
- Se nao entender, Lara pede esclarecimento de forma educada.
- Nao inventa dado factual.
- Nao entra em loop.

RODADA 6 - Evidencia e criterio de pronto
Ao final, entregue um relatorio com:
- commit usado;
- workflow id;
- status dos workflows ativos;
- health check do LangGraph;
- execucoes n8n usadas como evidencia;
- resultado dos testes locais;
- resultado dos testes via webhook qa_mode;
- resultado do teste real de slots;
- resultado do teste real de create appointment;
- prints ou caminhos dos arquivos de evidencia;
- lista de blockers restantes, se houver.

Criterio de pronto:
Somente declarar READY quando todos forem verdadeiros:
1. Apenas um fluxo responde ao numero de teste/producao.
2. LangGraph health OK de dentro do n8n.
3. Multi-turn nao reseta nome.
4. check_availability chama CRM.
5. Horarios exibidos vem do CRM.
6. Appointment so e criado apos motivo, contato e confirmacao.
7. CRM recebe dados preenchidos.
8. Endereco final esta correto.
9. Nao ha duplicidade de mensagem.
10. Nao ha handoff falso por falha tecnica.

Se qualquer item falhar:
- Nao diga que esta pronto.
- Registre o blocker.
- Corrija a menor causa tecnica possivel.
- Rode novamente a rodada que falhou e todas as rodadas anteriores impactadas.

Formato de resposta a cada rodada:
Resumo em 1 linha.
Diagnostico confirmado.
Arquivo/no alterado, se houve.
Teste executado.
Evidencia.
Proxima rodada.
```
