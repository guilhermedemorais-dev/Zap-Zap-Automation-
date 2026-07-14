# TASK-014: N8N - Lara V9 Shadow SDR

> Task e ordem de execucao. Aponta para specs, issue, branch e PR.

## Status visual
- Status visual: 🟡 Em andamento
- Status Kanban: In Progress
- Responsavel: Guilherme revisa; Codex/dev-workflow-standard orquestra; dev-implementation-standard executa blocos locais aprovados
- Issue criada / vinculada: https://github.com/guilhermedemorais-dev/ORION-CRM/issues/14
- Branch sugerida: `feat/lara-v9-shadow-sdr`
- Milestone: Lara V9
- Labels sugeridas: `feature`, `high-priority`, `needs-info`
- Pronto para GitHub Projects: sim

## Tipo
Feature / Arquitetura / QA

## Prioridade
P0

## Objetivo
Criar a Lara V9 como versao shadow, modelando o atendimento com arquitetura de estado, supervisor, agentes por responsabilidade, contrato JSON, memoria confiavel e QA real sem side effects, antes de qualquer alteracao em producao.

## Specs obrigatorias
- `docs/specs/lara-v9/module-spec.md`
- `docs/specs/lara-v9/validation-rules.md`
- `docs/specs/lara-v9/api.md`

## Docs obrigatorios
- `docs/LARA_REFERENCE_BENCHMARK_20260709.md`
- `docs/LARA_REFERENCE_REPOS_AUDIT.md`
- `docs/LARA_MASTER_EXECUTION_PLAN.md`
- `docs/LARA_ROOT_ARCHITECTURE.md`
- `docs/ORION_WF_BOT_V7_CURRENT_FLOW.md`
- `docs/LARA_QA_CONVERSATION_TESTS.md`
- `docs/LARA_WHATSAPP_SHADOW_TEST_RUNBOOK.md`
- `docs/LARA_V9_PRODUCTION_HANDOFF.md`

## Arquivos e modulos permitidos
Discovery/SDD:

- `docs/specs/lara-v9/`
- `docs/tasks/TASK-014-lara-v9-shadow-sdd.md`
- `qa/lara_qa_scenarios.json`
- documentos de arquitetura relacionados

Implementacao futura, somente apos aprovacao:

- workflow n8n duplicado V9 Shadow;
- scripts de patch/publicacao controlados;
- testes QA/smoke;
- possivel modulo externo LangGraph, se aprovado.

## Fora do escopo
- Alterar workflow de producao atual.
- Publicar V9 sem aprovacao humana.
- Criar chat local de QA nesta fase.
- Criar catalogo online.
- Alterar CRM sem spec propria.
- Remover ROOT.
- Fazer commit/push sem revisao do usuario.

## Estado atual encontrado
- Workflow atual da Lara existe e esta ativo no n8n como `ORION-WF-Bot-v7-LARA-SDR`, id `7SucjAi8zU69sQuT`.
- Numero WhatsApp de producao do cliente informado: `+55 47 9696-3593`.
- O fluxo atual tem funcionalidades uteis: WhatsApp, tratamento de mensagens, anti-loop, ROOT, CRM/agenda, delays, envio em blocos e QA parcial.
- Bugs reais confirmados:
  - `/rest` em sessao ROOT vira `modo_livre`;
  - `/reset` pode apagar configuracao sem confirmacao forte;
  - `Meu nome e Guilherme` pode virar `Perfeito, Meu`;
  - teste local anterior nao prova producao quando usa fixture esperada como saida.
- Repositorios de referencia mostram arquitetura melhor para atendimento:
  - contrato JSON;
  - memoria por lead/sessao;
  - supervisor;
  - agentes especialistas;
  - tools;
  - fallback.

## Resultado esperado
Ao final da implementacao futura:

- existe `LARA V9 Shadow` isolada da producao;
- QA roda contra resposta real do fluxo shadow;
- ROOT tem parser deterministico;
- ROOT vira console seguro de configuracao, com draft, preview/diff, confirmacao, versao, audit log e rollback;
- `/assumir` permite pausar a Lara e assumir uma conversa em atendimento humano;
- `/devolver` permite devolver a conversa para a Lara;
- reset exige confirmacao forte;
- nome e extraido corretamente;
- estado por numero evita repeticao e mistura de contexto;
- agenda so cria appointment apos dados minimos e confirmacao;
- catalogo/endereco/politicas vem de fonte definida;
- validador P0 bloqueia resposta antes de envio.

## Regras obrigatorias da implementacao
1. Nao mexer na producao sem backup e aprovacao.
2. Nao usar IA para decidir comando ROOT.
3. Nao usar IA para validar side effects.
4. Nao criar appointment em QA.
5. Nao enviar WhatsApp real em QA.
6. Nao tratar nome de perfil como confirmado.
7. Nao confirmar agenda sem CRM.
8. Nao inventar dados factuais.
9. Toda jornada P0 precisa de teste real no shadow.
10. Se qualquer teste P0 falhar, nao promover V9.
11. Nao usar o numero de producao `+55 47 9696-3593` para teste destrutivo, reset experimental ou QA com side effects.
12. ROOT Console deve salvar alteracoes por draft versionado, nunca por interpretacao livre direta.
13. `/assumir` deve pausar a Lara por conversa antes de qualquer resposta automatica.

## Checklist de execucao
1. Revisar specs V9.
2. Confirmar decisoes pendentes com Guilherme.
3. Duplicar workflow atual para `LARA V9 Shadow`.
4. Implementar parser deterministico ROOT.
5. Implementar ROOT Console com draft, preview/diff, confirmacao, versao, audit log e rollback.
6. Implementar `/assumir` e `/devolver`.
7. Implementar extrator deterministico de nome.
8. Implementar `State Controller`.
9. Implementar `Supervisor`.
10. Separar agentes/blocos por responsabilidade.
11. Implementar contrato JSON unico.
12. Implementar validador P0.
13. Implementar modo QA/shadow sem side effects.
14. Criar bateria de jornadas P0.
15. Rodar QA shadow e salvar evidencias.
16. Revisar com Guilherme.
17. So depois decidir promocao para producao.

## Prompt para o executor
Use esta task como contrato operacional. O SDD foi preparado, mas a execucao depende de revisao humana. Leia a task inteira e todas as specs obrigatorias antes de codar. Nao altere a producao. Crie a V9 como shadow isolada. Preserve as integracoes uteis da Lara atual e substitua o cerebro conversacional por estado, supervisor, agentes, contrato e validacao. Pare se precisar alterar CRM, credenciais, arquitetura de banco ou producao sem aprovacao.

## Condicoes de parada
- Falta de acesso ao n8n remoto.
- Falta de permissao para duplicar workflow.
- Ausencia de decisao sobre memoria duravel.
- Ausencia de numero de teste oficial para V9 Shadow.
- Ausencia do link oficial do catalogo se ele for exigido no teste.
- Qualquer risco de side effect real no modo QA.
- Divergencia entre spec e comportamento do CRM.

## Testes obrigatorios
- ROOT `/rest` nao entra em modo livre.
- ROOT `/reset` pede `CONFIRMAR RESET`.
- ROOT `/reset` + `cancelar` nao altera config.
- ROOT config cria draft e nao salva sem confirmacao.
- ROOT `/assumir` pausa resposta automatica para o cliente alvo.
- ROOT `/devolver` reativa resposta automatica para o cliente alvo.
- `Meu nome e Guilherme` extrai `Guilherme`.
- `Boa noite` pergunta nome e nao vira `Boa`.
- `Jhonatan` apos pergunta de nome avanca para descoberta.
- `qro agenda uma vizta` detecta intencao de agendamento.
- escolha de horario sem motivo nao cria appointment.
- motivo de visita e coletado e salvo no `crm_context`.
- resumo de agendamento pede confirmacao.
- appointment simulado so ocorre apos confirmacao.
- endereco oficial correto.
- catalogo usa link oficial quando configurado.
- QA/shadow nao envia WhatsApp real.
- QA/shadow nao cria appointment real.
- memoria isolada entre dois numeros.

## Evidencias esperadas no PR
- Link da issue.
- Specs V9 referenciadas.
- Workflow V9 Shadow exportado em `backups/`.
- Relatorio QA com inputs, outputs reais e status.
- Logs de bloqueio P0.
- Print ou JSON comprovando `/rest`, `/reset`, `Meu nome e Guilherme` e jornada de agendamento.
- Lista de arquivos alterados.
- Confirmacao de que producao nao foi alterada.

## Criterios de aceite
- Todas as specs obrigatorias foram lidas e respeitadas.
- V9 roda isolada.
- QA P0 passa contra output real do shadow.
- Nao ha side effects em QA.
- Bugs reais conhecidos estao cobertos por teste.
- Decisoes pendentes estao resolvidas ou marcadas como bloqueio.
- Guilherme aprova antes de promover para producao.

## Banco
Sem migracao nesta task Discovery/SDD.

Implementacao futura deve decidir memoria duravel antes de producao:

- preferencial: Postgres do CRM ou banco dedicado;
- aceitavel para shadow: Redis/n8n temporario com logs;
- nao recomendado como fonte principal: Google Sheets.

## API/Backend
Ver `docs/specs/lara-v9/api.md`.

## Frontend/UI
N/A nesta fase.

## Validacao
Validar com:

- `python3 -m json.tool qa/lara_qa_scenarios.json`
- testes locais de parser;
- QA shadow via n8n;
- comparacao de outputs reais.

## Riscos/Lacunas
- Memoria duravel ainda pendente.
- Board GitHub pode nao estar acessivel via CLI local.
- Catalogo oficial ainda precisa de link/fonte.
- LangGraph pode ser necessario depois, mas nao substitui parser/contrato/validador.

## Resultado da execucao
Execucao parcial iniciada em 2026-07-14.

### Bloco executado: runtime local V9 / guardrails P0

Arquivos alterados:

- `.gitignore`
- `lara_langgraph/graph.py`
- `lara_langgraph/root_console.py`
- `lara_langgraph/service.py`
- `scripts/lara_patch_v9_shadow_workflow.py`
- `scripts/lara_create_shadow_workflow.py`
- `scripts/lara_n8n_qa_smoke.py`
- `tests/test_lara_langgraph.py`
- `tests/test_lara_service.py`

Implementado:

- `human_takeover` no LangGraph: quando `state.human_takeover=true`, a Lara nao gera resposta automatica e retorna `next_action=none`.
- Parser ROOT deterministico em `lara_langgraph/root_console.py`.
- `/rest` e qualquer comando slash desconhecido viram `root_error`, nao modo livre.
- `/reset` cria `pending_action=reset` e exige `CONFIRMAR RESET`.
- `cancelar` cancela reset pendente sem alterar configuracao.
- comandos de configuracao como `/regra`, `/persona`, `/newprompt` criam draft pendente, nao salvamento direto.
- `/assumir [numero]` gera patch `human_takeover=true`.
- `/devolver [numero]` e `/bot [numero]` geram patch `human_takeover=false`.
- `qa_mode` foi incluido no contrato do runtime.
- resposta do runtime agora inclui `side_effects.send_whatsapp`, `side_effects.create_appointment` e `side_effects.update_crm`.
- em `qa_mode=true`, confirmacao de agenda retorna `next_action=simulate_appointment` e nao autoriza CRM/WhatsApp real.
- `.venv-langgraph/`, `__pycache__/` e `*.pyc` foram adicionados ao `.gitignore`.
- criado `scripts/lara_create_shadow_workflow.py` para gerar/criar workflow shadow inativo a partir do workflow atual.
- o script e `dry-run` por padrao e so cria workflow remoto com `--apply`.
- o script exige `N8N_API_KEY` via ambiente e nao contem token hardcoded.
- criado e aplicado `scripts/lara_patch_v9_shadow_workflow.py` no workflow shadow remoto.
- workflow shadow remoto criado: `LARA V9 Shadow SDR`, id `7kXu17NYpsN8Yc65`.
- webhook do shadow alterado para `whatsapp-inbound-v9-shadow`.
- workflow de producao permaneceu em `ORION-WF-Bot-v7-LARA-SDR`, id `7SucjAi8zU69sQuT`, webhook `whatsapp-inbound`.
- shadow ativado para permitir teste real pelo WhatsApp no path separado.
- patch remoto do shadow inclui parser ROOT deterministico, `/reset` com `CONFIRMAR RESET`, `/assumir` e `/devolver`.
- QA real encontrou regressao no shadow: `Meu nome é Guilherme` ainda retornava `Perfeito, Meu.` na execucao `3826`.
- regressao corrigida no shadow pelo guard `explicit_name_phrase_detected` no nó `Code: Parse Agent Output`.

Validacao executada:

- `.venv-langgraph/bin/python -m unittest tests.test_lara_langgraph -v`
  - Resultado: 17/17 testes passaram.
  - Inclui cobertura explicita para `Meu nome é Guilherme` salvar `Guilherme`.
  - Inclui cobertura de `qa_mode=true` bloqueando side effects reais.
- `.venv-langgraph/bin/python -m unittest discover -s tests -v`
  - Resultado: 18/18 testes passaram.
  - Inclui teste do endpoint FastAPI `/v1/lara/turn` expondo contrato `side_effects`.
- `.venv-langgraph/bin/python -m py_compile scripts/lara_create_shadow_workflow.py lara_langgraph/graph.py lara_langgraph/root_console.py lara_langgraph/service.py tests/test_lara_langgraph.py tests/test_lara_service.py`
  - Resultado: OK.
- `.venv-langgraph/bin/python scripts/lara_create_shadow_workflow.py --help`
  - Resultado: OK.
- `N8N_WORKFLOW_ID=7kXu17NYpsN8Yc65 N8N_WEBHOOK_PATH=whatsapp-inbound-v9-shadow .venv-langgraph/bin/python scripts/lara_n8n_qa_smoke.py --ids QA-01 --delay 14`
  - Resultado: execucao n8n `3824`.
  - Output real: `Olá, tudo bem?`, `Aqui é a Lara, consultora virtual da ORIN Joias.`, `Para que eu consiga te oferecer um atendimento mais preciso, você poderia me informar seu nome?`.
  - Side effects bloqueados: nenhum nó proibido de envio/CRM foi executado.
- Verificacao remota:
  - Producao: `7SucjAi8zU69sQuT`, active `true`, webhook `whatsapp-inbound`.
  - Shadow: `7kXu17NYpsN8Yc65`, active `true`, webhook `whatsapp-inbound-v9-shadow`.
- `N8N_WORKFLOW_ID=7kXu17NYpsN8Yc65 N8N_WEBHOOK_PATH=whatsapp-inbound-v9-shadow .venv-langgraph/bin/python scripts/lara_n8n_qa_smoke.py --ids QA-21 --delay 14`
  - Resultado: execucao n8n `3827`.
  - Output real corrigido: `Perfeito, Guilherme.`
  - `crm_context.customer_name`: `Guilherme`.
  - Side effects bloqueados: nenhum nó proibido de envio/CRM foi executado.
- `N8N_WORKFLOW_ID=7kXu17NYpsN8Yc65 N8N_WEBHOOK_PATH=whatsapp-inbound-v9-shadow .venv-langgraph/bin/python scripts/lara_n8n_qa_smoke.py --ids QA-02 QA-06 QA-07 QA-16 QA-17 QA-22 --delay 14`
  - Resultado: execucoes n8n `3828`, `3829`, `3830`, `3831`, `3832`, `3833`.
  - Side effects bloqueados: nenhum nó proibido de envio/CRM foi executado.
  - `QA-22` nao e valido nesse harness, porque ROOT exige admin/sessao e o payload fake comum segue fluxo de cliente.
- `N8N_WORKFLOW_ID=7kXu17NYpsN8Yc65 N8N_WEBHOOK_PATH=whatsapp-inbound-v9-shadow .venv-langgraph/bin/python scripts/lara_n8n_qa_smoke.py --ids QA-02 QA-17 QA-21 --delay 14`
  - Resultado: execucoes n8n `3837`, `3838`, `3839`.
  - Output real aprovado: `Prazer, Mariana.`, `Prazer, Jhonatan.`, `Prazer, Guilherme.`
  - `crm_context.customer_name`: `Mariana`, `Jhonatan`, `Guilherme`.
  - Side effects bloqueados: nenhum nó proibido de envio/CRM foi executado.
- `node scripts/lara_qa_runner.js --actual qa/lara_actual_outputs.json --allow-partial --ids QA-02,QA-17,QA-21`
  - Resultado: 3/3 cenarios reais passaram.
- `node scripts/lara_qa_runner.js`
  - Resultado: 22/22 cenarios passaram.
  - Limite: runner ainda esta em `expected_fixture`, portanto nao prova output real de producao/shadow.
- `node scripts/lara_workflow_logic_tests.js`
  - Resultado: 16/16 testes passaram.

- `N8N_WORKFLOW_ID=7kXu17NYpsN8Yc65 N8N_WEBHOOK_PATH=whatsapp-inbound-v9-shadow .venv-langgraph/bin/python scripts/lara_n8n_qa_smoke.py --ids QA-01 QA-02 QA-03 QA-04 QA-05 QA-06 QA-07 QA-08 QA-09 QA-10 QA-11 QA-12 QA-13 QA-14 QA-15 QA-16 QA-17 QA-18 QA-19 QA-20 QA-21 QA-22 --delay 14`
  - Resultado: execucoes n8n `3876` a `3897`.
  - Output real salvo em `qa/lara_actual_outputs.json`.
  - Relatorio salvo em `qa/lara_qa_report.json`.
  - Resultado do runner: 22/22 cenarios passaram em `actual_outputs`.
  - JSONL knowledge: OK, sem erros de parse.
  - Side effects bloqueados: nenhum no proibido de envio WhatsApp, CRM, agenda ou ROOT save foi executado nas 22 execucoes.
- Criado `scripts/lara_n8n_qa_journey.py` e `qa/lara_qa_journeys.json` para validar jornadas multi-turn com mesmo numero fake e historico QA injetado no shadow.
- `N8N_WORKFLOW_ID=7kXu17NYpsN8Yc65 N8N_WEBHOOK_PATH=whatsapp-inbound-v9-shadow .venv-langgraph/bin/python scripts/lara_n8n_qa_journey.py --delay 14`
  - Resultado: execucoes n8n `3931` a `3939`.
  - Relatorio salvo em `qa/lara_journey_report.json`.
  - Resultado: 3/3 jornadas multi-turn passaram.
  - Cobertura: abertura + nome + atendimento presencial, agendamento sem dados completos, descoberta de motivo e personalizacao/gravação.
  - Side effects bloqueados: nenhum no proibido de envio WhatsApp, CRM, agenda real ou ROOT save foi executado nas 9 execucoes.
- Regressao apos patch multi-turn:
  - `N8N_WORKFLOW_ID=7kXu17NYpsN8Yc65 N8N_WEBHOOK_PATH=whatsapp-inbound-v9-shadow .venv-langgraph/bin/python scripts/lara_n8n_qa_smoke.py --ids QA-01 QA-02 QA-03 QA-04 QA-05 QA-06 QA-07 QA-08 QA-09 QA-10 QA-11 QA-12 QA-13 QA-14 QA-15 QA-16 QA-17 QA-18 QA-19 QA-20 QA-21 QA-22 --delay 14`
  - Resultado: execucoes n8n `3940` a `3961`.
  - Resultado do runner: 22/22 cenarios passaram em `actual_outputs`.
  - Side effects bloqueados: nenhum no proibido nas 22 execucoes.
- `.venv-langgraph/bin/python -m unittest discover -s tests -v`
  - Resultado: 18/18 testes passaram.
- Criado `scripts/lara_production_readiness.py` para consolidar o gate de aprovacao:
  - confirma producao ativa em `7SucjAi8zU69sQuT` com webhook `whatsapp-inbound`;
  - confirma shadow ativo em `7kXu17NYpsN8Yc65` com webhook `whatsapp-inbound-v9-shadow`;
  - exige `qa/lara_qa_report.json` com 22/22 em `actual_outputs`;
  - exige `qa/lara_journey_report.json` com 3/3 jornadas;
  - reabre as execucoes n8n `3940` a `3961` e `3931` a `3939` para validar que nao houve side effects proibidos;
  - bloqueia aprovacao se o teste WhatsApp real ainda nao tiver sido aprovado.
- `N8N_API_KEY=... python3 scripts/lara_production_readiness.py`
  - Resultado: `BLOCKED`.
  - Bloqueio unico: `real_whatsapp_shadow_test`.
  - Relatorio salvo em `qa/lara_production_readiness_report.json`.
  - Todos os demais checks passaram.
- Criado `scripts/lara_prepare_production_promotion.py` para preparar a promocao da V9 sem aplicar por padrao:
  - usa o shadow `7kXu17NYpsN8Yc65` como fonte;
  - preserva o nome da producao `ORION-WF-Bot-v7-LARA-SDR`;
  - troca o webhook do payload para `whatsapp-inbound`;
  - gera backup da producao, backup do shadow e payload de promocao em `backups/`;
  - `--apply` exige readiness aprovado e confirmacao textual `PROMOVER LARA V9 PARA PRODUCAO`.
- `N8N_API_KEY=... python3 scripts/lara_prepare_production_promotion.py --allow-blocked-dry-run`
  - Resultado: dry-run OK, sem alterar producao.
  - Backups/payload:
    - `backups/n8n-lara-prod-before-v9-promotion-20260714-162000.json`
    - `backups/n8n-lara-shadow-source-for-v9-promotion-20260714-162000.json`
    - `backups/n8n-lara-prod-v9-promotion-payload-20260714-162000.json`
- `N8N_API_KEY=... python3 scripts/lara_prepare_production_promotion.py --apply --confirm 'PROMOVER LARA V9 PARA PRODUCAO'`
  - Resultado esperado e confirmado: bloqueado por `real_whatsapp_shadow_test`.
  - Producao permaneceu intacta: `7SucjAi8zU69sQuT`, active `true`, webhook `whatsapp-inbound`, 152 nos, 125 conexoes.
- Criado contrato de evidencia para teste WhatsApp real:
  - `qa/lara_whatsapp_shadow_test.example.json`
  - `scripts/lara_init_whatsapp_evidence.py`
  - `qa/lara_whatsapp_shadow_test.json` criado com status `PENDING`.
- `scripts/lara_production_readiness.py` foi endurecido:
  - remove aprovacao por flag solta;
  - passa a exigir `qa/lara_whatsapp_shadow_test.json`;
  - exige `status=APPROVED`, `approved_by_user=true`, URL do shadow correta, checklist 100% verdadeiro, zero falhas registradas e pelo menos screenshot ou execution id como evidencia.
- `N8N_API_KEY=... python3 scripts/lara_production_readiness.py`
  - Resultado: `BLOCKED`.
  - Bloqueio: `real_whatsapp_shadow_test`.
  - Detalhe: arquivo existe, mas status `PENDING`, checklist incompleto e sem evidencias.
- Criado runbook operacional:
  - `docs/LARA_WHATSAPP_SHADOW_TEST_RUNBOOK.md`
  - Define mensagens exatas, esperado, critérios de reprovação, preenchimento de evidência e comandos finais.
- Criado handoff de produção:
  - `docs/LARA_V9_PRODUCTION_HANDOFF.md`
  - Consolida estado remoto, gate, evidencia obrigatoria e comando de promocao.
- Criado utilitário de registro:
  - `scripts/lara_record_whatsapp_evidence.py`
  - Registra tester, numero de teste, execution ids, screenshots, notas, falhas e aprovação.
  - Impede aprovação sem screenshot ou execution id.
  - Impede aprovação se houver falhas registradas.
- Validacao executada:
  - `python3 -m py_compile scripts/lara_record_whatsapp_evidence.py scripts/lara_init_whatsapp_evidence.py scripts/lara_production_readiness.py`
  - `python3 -m json.tool qa/lara_whatsapp_shadow_test.json`
  - `python3 -m json.tool qa/lara_whatsapp_shadow_test.example.json`
  - `N8N_API_KEY=... python3 scripts/lara_production_readiness.py`
  - Resultado: readiness segue `BLOCKED` por `real_whatsapp_shadow_test`, como esperado.

Bloqueios restantes para producao:

- V9 Shadow ja existe no n8n remoto e esta ativa com webhook separado.
- QA real em modo shadow/QA passou 22/22 contra output real do n8n.
- ROOT `/rest` foi validado pelo harness ROOT QA remoto na execucao `3897`.
- QA multi-turn em modo shadow/QA passou 3/3 contra output real do n8n.
- QA de contrato de entrada passou 4/4 contra o webhook shadow remoto:
  - UAZAPI atual;
  - Evolution/Baileys `messages.upsert`;
  - payload com `data.text`;
  - payload achatado defensivo.
- O nó `Filter UAZAPI` do shadow foi endurecido para aceitar variações comuns de payload WhatsApp/provedor sem depender de um único formato artificial.
- Apos o patch de entrada, a bateria remota foi reexecutada:
  - single-turn: 22/22, execucoes `4008` a `4029`;
  - multi-turn: 3/3, execucoes `4039` a `4047`;
  - contrato de entrada: 4/4, execucoes `3982` a `3985`.
- `scripts/lara_production_readiness.py` agora coleta os IDs single-turn do arquivo `qa/lara_actual_outputs.json`, em vez de depender de faixa fixa hardcoded.
- Ainda falta QA real via WhatsApp no numero de teste apontado para o webhook shadow.
- Memoria duravel de producao ainda nao foi definida, `InMemorySaver` serve apenas para QA/local.
- Promocao para producao continua bloqueada ate teste WhatsApp real e aprovacao humana.
