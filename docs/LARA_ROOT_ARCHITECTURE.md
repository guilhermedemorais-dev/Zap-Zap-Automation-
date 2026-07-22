# Lara ROOT Architecture

## Resumo

O ROOT é a camada administrativa da Lara. Ele registra as instruções de atendimento em Redis e injeta essas instruções no contexto do AI Agent em tempo de execução.

Regra operacional: comportamento da Lara deve ser alterado pelo ROOT. O workflow n8n só deve ser alterado para bugs técnicos de integração, roteamento, parsing, CRM, Redis, UAZAPI ou segurança.

## Fonte De Verdade

### Configuração viva da Lara

- Chave Redis: `LARA_ROOT_CONFIG`
- Nó que lê para comandos admin: `ROOT: Ler Config Redis`
- Nó que salva comandos confirmados: `ROOT: Salvar Config Redis`
- Nó que lê antes da Lara responder cliente: `ROOT: Carregar Config LLM`
- Nó que injeta no contexto do AI Agent: `ROOT: Injetar Regras`

O prompt criado via ROOT não fica salvo no `AI Agent systemMessage`. Ele fica em `LARA_ROOT_CONFIG`, normalmente no campo `custom_prompt`, quando usado `/newprompt`.

### Fonte factual da Lara

Informações de produto, catálogo, FAQ, loja, políticas e links oficiais devem ter duas versões:

- versão visual no ROOT ou painel futuro, para humano revisar e configurar;
- versão JSON/JSONL compacta, para o n8n buscar e a IA consumir com baixo custo de token.

A documentação da camada fica em:

`docs/LARA_RAG_JSONL_ARCHITECTURE.md`

Regra:

- `BASE_LARA` define como a Lara se comporta;
- `root_blocks` define roteamento e blocos de conversa;
- `knowledge/*.jsonl` define os fatos consultáveis atuais;
- `catalogo/*.jsonl` fica reservado para fase futura, quando existir catálogo online oficial;
- CRM define contexto privado do cliente e agenda.

Não colocar catálogo inteiro dentro de `BASE_LARA`, `custom_prompt` ou bloco situacional.

### Contrato técnico do AI Agent

O `AI Agent systemMessage` deve ser mantido fino. Ele define formato JSON, ações técnicas e regras de segurança mínimas.

Não usar o `AI Agent systemMessage` para ajustar:

- tom da Lara;
- saudação;
- personalidade;
- confirmação de nome;
- condução comercial;
- exemplos de atendimento;
- regras de escrita;
- regras de agendamento conversacional.

Esses itens são ROOT.

## Estrutura Do `LARA_ROOT_CONFIG`

Campos principais:

- `custom_prompt`: prompt principal criado via `/newprompt`.
- `root_blocks`: arquitetura V8 com `base_lara`, `router`, blocos comerciais e schema de `crm_context`.
- `persona_extra`: personalidade criada via `/persona`.
- `objetivos`: lista criada via `/objetivo`.
- `rules`: regras criadas via `/regra`.
- `write_rules`: regras de escrita criadas via `/escrita`.
- `corrections`: correções criadas via `/corrigir`.
- `examples`: exemplos criados via `/exemplo entrada:X|saida:Y`.
- `links`: links criados via `/link nome|url|descrição`.
- `tom`: tom numérico criado via `/tom`.
- `audit_log`: histórico das últimas alterações feitas no ROOT, com data, número do admin, ação e resumo.
- `_pending`: alteração aguardando confirmação `sim` ou `não`.

## Fluxo De Leitura Do ROOT

1. Cliente envia mensagem.
2. Workflow normaliza entrada.
3. `Context Refiner` monta contexto.
4. `ROOT: Carregar Config LLM` lê `LARA_ROOT_CONFIG`.
5. `ROOT: Injetar Regras` transforma o JSON do ROOT em texto de instrução.
6. `AI Agent` recebe:
   - histórico/contexto;
   - mensagem atual;
   - data atual;
   - nome do perfil, quando existir;
   - `ROOT_CONFIG` injetado.
7. Lara responde em JSON.

## Fluxo De Escrita Do ROOT

1. Admin entra em modo ROOT pelo WhatsApp com `root` ou `/root`.
2. `ROOT: Parser de Comando` identifica o comando.
3. `ROOT: Ler Config Redis` lê `LARA_ROOT_CONFIG`.
4. `ROOT: Processar Comando` gera `_pending` ou aplica leitura.
5. Se houver confirmação, `ROOT: Salvar Config Redis` grava a nova configuração.

Comandos que mudam configuração:

- `/newprompt`
- `/setblock nome|texto`
- `/persona`
- `/objetivo`
- `/regra`
- `/escrita`
- `/corrigir`
- `/exemplo`
- `/link`
- `/tom`
- `/reset`

Comandos de leitura:

- `/status`
- `/parametro`
- `/prompt`
- `/blocks`
- `/block [nome]`
- `/log`
- `/help`
- `/tutorial`

## ROOT Blocks V8

`root_blocks` separa o comportamento da Lara em:

- `BASE_LARA EFETIVA`: identidade, tom, limites, fontes oficiais e regras globais, montada com `root_blocks.base_lara` mais os ajustes globais do ROOT clássico.
- `ROUTER`: classificação de intenção, etapa comercial, temperatura do lead e próxima ação.
- `blocks`: blocos situacionais, como `ABERTURA`, `INFORMACOES`, `CATALOGO`, `AGENDAMENTO`, `POS_AGENDAMENTO`, `HUMANO` e `FORA_ESCOPO`.
- `crm_context_schema`: campos mínimos enviados ao CRM para ajudar o atendente.

`root_blocks` não deve carregar base extensa de produto. O bloco `CATALOGO` deve orientar quando consultar a camada RAG JSONL, e o buscador interno deve injetar somente resultados relevantes em `RAG_CONTEXT`.

Comandos:

- `/persona`, `/tom`, `/objetivo`, `/regra`, `/escrita`, `/corrigir`, `/exemplo` e `/link`: ajustam a base global da Lara.
- `/blocks`: lista blocos ativos.
- `/block AGENDAMENTO`: mostra um bloco.
- `/setblock AGENDAMENTO|texto`: atualiza um bloco após confirmação.

## Auditoria Do ROOT

O comando `/log` mostra as últimas alterações registradas no ROOT.

Cada registro guarda:

- data e hora;
- número do admin;
- ação executada;
- resumo do conteúdo alterado.

O histórico fica no campo `audit_log` dentro de `LARA_ROOT_CONFIG` e mantém as últimas 30 alterações.

Limitação: o log não reconstrói alterações antigas feitas antes da ativação da auditoria. Ele passa a valer para modificações feitas depois desta atualização.
- `/help`
- `/menu`

## RAG JSONL Planejada

A próxima camada planejada é uma fonte factual separada:

```text
Site/API/scraper
→ knowledge/*.jsonl agora
→ catalogo/*.jsonl no futuro, quando houver catálogo oficial
→ buscador interno
→ RAG_CONTEXT compacto
→ Lara responde com evidência ou cai em fallback
```

Comandos ROOT planejados:

- `/rag status`: última sincronização, total de itens e erros.
- `/rag produto [termo]`: teste de busca no catálogo.
- `/rag faq [termo]`: teste de busca na base de conhecimento.
- `/rag fonte [id]`: visualizar item bruto.
- `/rag log`: histórico de sincronização e bloqueios.

Esses comandos ainda não fazem parte do workflow atual. Eles devem ser implementados somente depois do schema JSONL e do buscador interno.

## Como Puxar O Prompt Atual Sem Alterar Nada

Opção correta: ler diretamente a chave Redis `LARA_ROOT_CONFIG`.

Se não houver acesso direto ao Redis, usar leitura passiva de execuções existentes do n8n:

1. Buscar execuções recentes do workflow `ORION-WF-Bot-v7-LARA-SDR`.
2. Procurar nós:
   - `ROOT: Ler Config Redis`
   - `ROOT: Processar Comando`
   - `ROOT: Injetar Regras`
3. Extrair `propertyName` do nó `ROOT: Ler Config Redis`.
4. Parsear esse JSON como `LARA_ROOT_CONFIG`.

Não disparar `root`, `/status` ou `/parametro` no WhatsApp apenas para descobrir estado, porque isso cria mensagem real no canal.

## Limite Entre ROOT E Workflow

### Mexer pelo ROOT

- Como a Lara cumprimenta.
- Se pergunta nome.
- Se confirma nome do perfil.
- Como separa frases em balões.
- Como conduz agendamento.
- Como retoma após inatividade.
- Como finaliza atendimento.
- Como pede motivo da visita.
- Tom humano, comercial e consultivo.

### Mexer no workflow n8n

- Loop de mensagens próprias.
- Deduplicação.
- Erro de JSON.
- Integração com CRM.
- Falha de Redis.
- Falha UAZAPI.
- Parser quebrado.
- Endpoint errado.
- Credencial.
- Roteamento incorreto de nós.

## Estado De Rollback

Em 2026-06-26, o workflow foi restaurado para:

`backups/n8n-ORION-WF-Bot-v7-LARA-SDR-before-maintenance-20260625-194542.json`

Validação pós-rollback:

- `customer_whatsapp`: removido.
- `whatsapp_profile_name`: removido.
- contrato `IDENTIDADE DO CLIENTE`: removido.
- loop guard novo: removido.
- parser `hasCommercialIntent`: removido.

## Regra Para Trabalhos Futuros

Antes de qualquer ajuste:

1. Identificar se é comportamento ou bug técnico.
2. Se for comportamento, alterar via ROOT.
3. Se for bug técnico, fazer backup do workflow ativo antes.
4. Nunca alterar `AI Agent systemMessage` para ajustar atendimento sem aprovação explícita.
5. Nunca disparar comando WhatsApp quando a tarefa for só leitura, salvo autorização explícita.
