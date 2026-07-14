# MODULE SPEC: Lara LangGraph Runtime

## Status
Em revisão

## Product Spec relacionado
HIPÓTESE: não existe Product Spec formal único da Lara neste repositório. Esta spec deriva de `docs/LARA_MASTER_EXECUTION_PLAN.md`, `docs/LARA_REFERENCE_REPOS_AUDIT.md`, `docs/LARA_ROOT_ARCHITECTURE.md` e dos incidentes de atendimento reportados.

## Objetivo
Separar o controle conversacional da Lara do prompt livre do n8n, usando LangGraph como runtime de estado, intenção, decisão e contrato JSON para reduzir alucinação, repetição de saudação, mistura de nomes e agendamento incompleto.

## Escopo incluído
- Runtime Python com LangGraph.
- Grafo de estados para identificação, descoberta, catálogo/informações, agendamento e encerramento.
- Memória curta por `thread_id`, usando checkpointer do LangGraph.
- API HTTP para o n8n chamar.
- Contrato JSON para `reply`, `check_availability` e `create_appointment`.
- Testes de jornada para saudação, nome, erro de digitação, agenda, motivo e confirmação.
- Documentação de integração n8n.

## Fora de escopo
- Publicar no n8n remoto sem URL estável do serviço.
- Migrar ROOT para fora do n8n.
- Substituir CRM.
- Criar catálogo online ou links de produto inexistentes.
- Deploy em produção sem QA remoto em número de teste.

## Páginas/telas previstas
N/A. Módulo backend/runtime sem UI.

## Componentes compartilhados
N/A. Não há componentes de frontend.

## Regras de negócio do módulo
- Saudação não pode virar nome.
- Nome de perfil do WhatsApp não é nome confirmado.
- Nome só vira confirmado após resposta explícita do cliente.
- Depois do nome confirmado, a Lara não repete a abertura.
- Agendamento não pode ser criado sem motivo da visita.
- Agendamento só pode ser criado após resumo e confirmação do cliente.
- Endereço oficial obrigatório: `Av. Brasil, 1500 - Centro, Balneário Camboriú - SC, 88330-901`.
- Link de produto não pode ser inventado enquanto não houver catálogo oficial.
- Cada número/sessão deve ter memória isolada por `thread_id`.

## Banco
Impacto indireto. O runtime deve usar checkpointer do LangGraph para memória curta. Para produção, a opção recomendada é Postgres com `thread_id` por número de WhatsApp. A primeira versão local pode usar `InMemorySaver` apenas para teste e desenvolvimento.

## API/Backend
Criar serviço HTTP local/contêiner:

- `GET /health`
- `POST /v1/lara/turn`

Detalhe em `docs/specs/lara-langgraph/api.md`.

## Frontend/UI
N/A. Sem interface.

## Testes
- Unit tests de jornadas de conversa.
- Smoke HTTP local.
- Futuro QA remoto via n8n em número de teste.

## Segurança
- Não registrar token n8n, token UAZAPI, chaves OpenAI ou dados sensíveis em logs.
- Serviço LangGraph não deve ficar público sem autenticação/rede restrita.
- `session_id`/`thread_id` deve ser derivado deterministicamente do número ou conversa, nunca por IA.
- Payloads de ferramenta devem ser validados antes do n8n executar CRM.

## Observabilidade/logs
- Logar `session_id`, `intent`, `conversation_stage`, `next_action` e erro sanitizado.
- Não logar prompt completo com dados pessoais em produção sem política definida.
- Expor `/health`.

## Dependências
- Python 3.12.
- LangGraph, validado contra repositório oficial `langchain-ai/langgraph`, commit `5931a5f`.
- FastAPI/Uvicorn para API HTTP.
- n8n remoto deve conseguir chamar URL do serviço.

## Riscos
- Serviço sem URL estável impede integração remota.
- `InMemorySaver` perde memória em restart, não serve como memória definitiva de produção.
- Expor serviço publicamente sem autenticação cria vetor de abuso.
- Alterar n8n direto sem fallback pode derrubar atendimento.

## Decisões pendentes
1. Onde hospedar o serviço LangGraph: VPS do n8n, servidor do CRM ou outro ambiente?
2. Qual backend de checkpointer em produção: Postgres do CRM, Postgres próprio ou Redis/alternativa?
3. Qual autenticação entre n8n e serviço LangGraph?

## Critérios de aceite
- Testes locais de jornada passam.
- Serviço responde `/health`.
- `POST /v1/lara/turn` retorna contrato JSON válido.
- Mesma `session_id` mantém estado via checkpointer quando o n8n não envia `state`.
- Saudação não vira nome.
- Agendamento exige motivo e confirmação antes de `create_appointment`.

## Hipóteses
- HIPÓTESE: o n8n remoto poderá chamar uma URL HTTPS do runtime LangGraph.
- HIPÓTESE: o CRM aceitará receber `crm_note` e dados enriquecidos como já documentado em versões anteriores.
