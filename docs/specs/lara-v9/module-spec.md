# MODULE SPEC: Lara V9 Shadow SDR

> Spec e contrato do que deve ser construido. Nao e PR, nao e task.

## Status
Em revisao

## Product Spec relacionado
HIPOTESE: nao existe Product Spec formal unico da Lara neste repositorio.

Esta spec deriva de:

- `docs/LARA_MASTER_EXECUTION_PLAN.md`
- `docs/LARA_REFERENCE_REPOS_AUDIT.md`
- `docs/LARA_REFERENCE_BENCHMARK_20260709.md`
- `docs/LARA_ROOT_ARCHITECTURE.md`
- `docs/ORION_WF_BOT_V7_CURRENT_FLOW.md`
- incidentes reais reportados no WhatsApp: `/rest`, `/reset`, `Meu nome e Guilherme`, repeticao de saudacao, agenda sem contexto e endereco incorreto.

## Objetivo
Criar a arquitetura da Lara V9 como uma versao shadow do fluxo atual, aproveitando as integracoes existentes da Lara e modelando o atendimento com os padroes que funcionam nos repositorios de referencia: estado explicito, supervisor, agentes por responsabilidade, contrato JSON, validadores P0 e QA real antes de producao.

## Escopo incluido
- Desenhar a V9 como copia isolada do fluxo atual, sem substituir producao no primeiro momento.
- Manter entrada WhatsApp/UAZAPI, tratamento de mensagens, anti-loop, delay por bloco, ROOT, CRM/agenda e envio.
- Reestruturar o cerebro conversacional com:
  - `State Controller`
  - `Supervisor`
  - `Agent Identity`
  - `Agent Discovery`
  - `Agent Catalog Info`
  - `Agent Appointment`
  - `Agent Handoff`
  - `Contract Validator`
- Definir memoria confiavel por numero.
- Definir contrato JSON unico para resposta, ferramentas e CRM.
- Definir regras deterministicas para nome, comandos ROOT e reset.
- Rebaixar ROOT para `ROOT Console`: console seguro de configuracao versionada, nao cerebro livre da Lara.
- Incluir takeover humano com `/assumir` e `/devolver` para pausar/resumir a Lara por conversa.
- Definir QA de jornada com execucao real em modo shadow/QA, sem enviar WhatsApp real e sem criar agendamento real.
- Definir criterios para futura migracao parcial ou total para LangGraph.

## Fora de escopo
- Publicar V9 direto em producao sem validacao.
- Apagar ou substituir o workflow atual da Lara.
- Criar catalogo online do zero.
- Criar UI local de chat para teste nesta fase.
- Alterar CRM sem spec propria do Orion CRM.
- Reescrever ROOT inteiro sem preservar comandos existentes.
- Prometer ausencia total de bugs.

## Paginas/telas previstas
N/A. Esta fase nao cria UI.

Futuro opcional:

- painel visual do ROOT;
- painel de QA;
- diagrama visual de estados.

## Componentes compartilhados
N/A no frontend.

Componentes logicos previstos:

- `State Controller`
- `Root Command Parser`
- `Root Config Versioning`
- `Human Takeover Controller`
- `Name Extractor`
- `Supervisor Router`
- `Agent Identity`
- `Agent Discovery`
- `Agent Catalog Info`
- `Agent Appointment`
- `Agent Handoff`
- `Contract Validator`
- `QA Harness`

## Regras de negocio do modulo
Detalhe em `docs/specs/lara-v9/validation-rules.md`.

Resumo:

- comando administrativo nao pode cair em modo livre;
- `/reset` deve exigir confirmacao forte;
- `/assumir` deve pausar a Lara para uma conversa especifica;
- `/devolver` deve devolver a conversa para a Lara;
- nome so vira confirmado quando extraido de fala explicita ou resposta de nome;
- saudacao, horario, confirmacao curta e comando nunca viram nome;
- IA nao pode criar appointment diretamente sem validacao;
- facts como endereco, link, catalogo, politica e horario devem vir de fonte definida;
- agendamento exige estado, dados minimos, motivo e confirmacao;
- resposta final deve passar no validador P0 antes de envio.

## Banco
Impacto previsto, sem migracao nesta Discovery.

Recomendacao:

- Redis: buffer curto, anti-loop, deduplicacao e historico recente.
- Banco duravel, preferencialmente Postgres do CRM ou banco dedicado: estado oficial por numero, dados coletados, auditoria e logs de decisao.
- CRM: fonte oficial de agenda, leads e appointments.
- JSONL/RAG: fonte factual versionada para loja, links, catalogo, politicas e respostas frequentes.

HIPOTESE: o CRM possui ou pode receber campos de `ai_context`, `crm_note`, `intent`, `appointment_reason` e metadados de atendimento.

## API/Backend
Detalhe em `docs/specs/lara-v9/api.md`.

Escopo conceitual:

- webhook QA/shadow que roda a V9 sem side effects;
- contrato interno `POST /v9/turn` ou subworkflow n8n equivalente;
- chamada para CRM `check_availability`;
- chamada para CRM `create_appointment`;
- atualizacao de lead/contexto;
- logs/auditoria.

## Frontend/UI
N/A nesta fase.

## Testes
Obrigatorio testar jornadas completas, nao apenas frases soltas:

- ROOT `/rest`
- ROOT `/reset`
- saudacao simples
- frase de nome: `Meu nome e Guilherme`
- resposta so com primeiro nome
- erro de digitacao: `qro agenda uma vizta`
- pedido de catalogo
- pedido de endereco
- pedido de agendamento
- escolha de horario
- coleta de motivo
- resumo e confirmacao
- criacao de appointment simulada
- handoff humano
- memoria isolada por numero

## Seguranca
- Tokens e segredos sempre em credenciais/ambiente, nunca em Set/Code node ou docs.
- LLM output e sempre entrada nao confiavel.
- Ferramentas com efeito colateral precisam de validador antes.
- Modo QA/shadow deve bloquear WhatsApp real e CRM real.
- Logs nao devem expor token, chaves ou dados sensiveis alem do necessario.
- ROOT deve ter autorizacao por numero e audit log.

## Observabilidade/logs
Eventos minimos:

- `message_received`
- `root_command_received`
- `root_config_draft_created`
- `root_config_confirmed`
- `human_takeover_started`
- `human_takeover_finished`
- `state_loaded`
- `intent_detected`
- `agent_selected`
- `contract_generated`
- `contract_rejected`
- `tool_requested`
- `tool_blocked`
- `message_sent`
- `state_saved`
- `appointment_simulated`
- `appointment_created`

Campos minimos:

- `conversation_id`
- `whatsapp_number`
- `state_before`
- `state_after`
- `intent`
- `agent`
- `next_action`
- `blocked_reason`
- `qa_mode`
- `workflow_version`

## Dependencias
- Workflow atual `ORION-WF-Bot-v7-LARA-SDR`, id `7SucjAi8zU69sQuT`.
- Numero WhatsApp de producao do cliente: `+55 47 9696-3593`.
- Repositorios de referencia clonados:
  - `reference-repos/sdr-evolufit`
  - `reference-repos/Sistema-SDR-Multiagentes`
- n8n remoto.
- CRM/agenda Orion/ORIN.
- UAZAPI/WhatsApp.
- ROOT Admin atual.
- `knowledge/*.jsonl`.

## Riscos
- Reescrever tudo de uma vez vira nova gambiarra.
- Copiar fluxo imobiliario literalmente quebra no dominio joalheria.
- Manter a IA decidindo comandos e ferramentas repete os bugs atuais.
- Teste local que valida fixture esperada contra fixture esperada gera falsa seguranca.
- Memoria apenas em Redis pode perder estado ou misturar contexto se a chave for errada.
- LangGraph sem contrato, parser e fonte factual nao resolve alucinacao sozinho.

## Decisoes pendentes
1. Onde ficara a memoria duravel da V9: Postgres do CRM, banco proprio, n8n Data Table ou outra opcao?
2. A V9 sera implementada primeiro 100% dentro do n8n ou com runtime externo LangGraph?
3. Qual sera o campo oficial do CRM para salvar resumo do atendimento da Lara?
4. Qual link oficial do catalogo deve entrar como fonte factual?
5. Quais numeros terao permissao ROOT na V9?
6. Qual sera o numero de teste oficial da V9 Shadow?
7. O fluxo atual continua ativo enquanto a V9 roda como shadow no numero de teste?

## Criterios de aceite
- Existe workflow V9 shadow ou especificacao executavel aprovada antes de mexer na producao.
- ROOT nao interpreta comando desconhecido como modo livre.
- `/reset` exige confirmacao forte antes de apagar configuracao.
- `Meu nome e Guilherme` extrai `Guilherme`, nao `Meu`.
- Saudacao nao vira nome.
- Nome de perfil nao vira nome confirmado.
- Cada numero tem estado isolado.
- Agendamento nao cria appointment sem motivo, dados minimos e confirmacao.
- Resposta factual vem de fonte definida.
- QA real em modo shadow captura a resposta gerada pelo fluxo, nao apenas fixture esperada.
- Nenhuma chamada real de WhatsApp ou CRM ocorre em modo QA.

## Hipoteses
- HIPOTESE: e possivel duplicar o workflow atual no n8n remoto para criar `LARA V9 Shadow`.
- HIPOTESE: o n8n consegue executar modo QA sem side effects como ja foi usado em rodadas anteriores.
- HIPOTESE: o CRM possui endpoints ou rotas n8n para agenda e appointment ja utilizaveis.
- HIPOTESE: o catalogo oficial sera fornecido como link unico antes da V9 entrar em producao.
- HIPOTESE: o numero `+55 47 9696-3593` e o numero definitivo de producao do cliente e nao deve ser usado para QA destrutivo.
