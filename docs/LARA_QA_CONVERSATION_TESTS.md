# QA De Conversas Da Lara

## Resumo

Este documento simula conversas reais de cliente com a Lara para validar comportamento, tom, memória, agendamento, fallback e risco de alucinação.

Status deste QA:

- tipo: QA conversacional offline;
- objetivo: validar a resposta esperada da Lara antes de testar no n8n real;
- não dispara WhatsApp;
- não cria agendamento real;
- não altera CRM;
- não substitui teste ponta a ponta no número de teste.

## Status Remoto Em 2026-06-30

Workflow remoto: `ORION-WF-Bot-v7-LARA-SDR`, id `7SucjAi8zU69sQuT`, ativo com 152 nós após os hotfixes.

Alterações validadas no remoto:

- `qa_mode` intercepta antes de WhatsApp/CRM e não dispara efeito colateral nos testes.
- `Code: Parse Agent Output` força coleta de dia, nome completo e motivo quando o cliente escolhe apenas horário.
- `Code: Parse Agent Output` força pergunta de nome quando há saudação com intenção comercial e nome ainda não confirmado.
- `Redis Chat Memory` recebeu `contextWindowLength = 8`.
- `Global Variables.max_chat_history` foi reduzido de `40` para `12`.
- `ROOT: Injetar Regras` agora envia `ROOT_CONFIG RUNTIME COMPACTO`, mantendo o ROOT completo armazenado, mas reduzindo o prompt vivo.

Evidências remotas:

- QA-09, execução `3744`: aprovado. Resposta pediu dia, nome completo e motivo da visita. ROOT runtime medido em `6897` caracteres.
- QA-13, execução `3746`: aprovado. Resposta perguntou o nome e não herdou nome de conversa anterior. ROOT runtime medido em `7323` caracteres.
- Delay de envio aplicado em 2026-06-30: `Code: Enviar Blocos` aguarda `10s` antes do primeiro bloco de resposta normal e `3s` antes de resposta pós-ação; `Code: Enviar Pre-Blocos` aguarda `10s` antes da primeira mensagem preliminar de action.

Backups principais:

- `backups/n8n-ORION-WF-Bot-v7-after-runtime-root-compact-final-20260630.json`
- `backups/n8n-ORION-WF-Bot-v7-after-identity-parser-guard-20260630.json`
- `backups/n8n-ORION-WF-Bot-v7-after-response-delay-20260630.json`

Critério geral de aprovação:

- Lara não inventa preço, estoque, prazo, produto, link ou política;
- Lara não usa nome de perfil como nome confirmado;
- Lara conduz o cliente com naturalidade;
- Lara faz no máximo uma ou duas perguntas por resposta;
- Lara separa mensagens em blocos curtos;
- Lara só confirma agendamento depois da ação técnica de criação no CRM;
- Lara registra contexto útil para o atendente.

## Matriz De Risco

| Área | Risco | Gravidade | Critério de reprovação |
|---|---|---:|---|
| Nome | usar nome de outro cliente ou perfil sem confirmar | P0 | chama cliente por nome não informado |
| Agenda | confirmar sem CRM | P0 | diz "agendado" antes de `create_booking` |
| Produto | inventar catálogo/link/preço | P0 | manda produto, preço ou URL não confirmada |
| Memória | misturar conversa anterior | P0 | responde assunto antigo ou nome errado |
| Escrita | texto institucional longo | P1 | manda parágrafo grande ou menu embolado |
| CRM | não coletar intenção | P1 | cria agenda sem motivo real da visita |
| Handoff | insistir quando não sabe | P1 | inventa em vez de encaminhar |

## QA-01: Saudação Sem Nome

### Entrada

Cliente:

```text
Olá
```

### Resposta Esperada

Lara:

```text
Olá, tudo bem? Sou a Lara, consultora virtual da ORIN Joias.
```

```text
Pra te atender melhor, qual é o seu nome?
```

```text
Posso te ajudar com uma joia para uma ocasião especial, personalização ou agendamento.
```

### Aprovação

- pergunta o nome;
- não usa nome de perfil;
- não manda texto institucional longo;
- não fala de catálogo online com link direto.

### Status

Aprovado como comportamento esperado.

## QA-02: Cliente Informa Nome

### Entrada

Cliente:

```text
Meu nome é Mariana
```

### Resposta Esperada

Lara:

```text
Prazer, Mariana.
```

```text
Me conta o que você está buscando hoje: alianças, uma joia para presente, personalização ou um horário para atendimento?
```

### Aprovação

- registra nome informado pelo cliente;
- não repete saudação inicial;
- segue para descoberta.

### Status

Aprovado como comportamento esperado.

## QA-03: Cliente Pede Catálogo

### Entrada

Cliente:

```text
Vocês têm catálogo?
```

### Resposta Esperada

Lara:

```text
Ainda não tenho um catálogo online com link direto das peças.
```

```text
Mas posso te ajudar por aqui e encaminhar para uma especialista verificar as opções disponíveis.
```

```text
Você está procurando alianças, anel, colar, brinco ou uma joia personalizada?
```

### Aprovação

- não inventa catálogo online;
- não manda link falso;
- conduz para intenção.

### Status

Aprovado como comportamento esperado.

## QA-04: Cliente Pergunta Produto Específico

### Entrada

Cliente:

```text
Tem aliança em ouro 17k de 3mm?
```

### Resposta Esperada

Lara:

```text
Ainda não tenho um catálogo online com link direto desse modelo.
```

```text
Mas consigo encaminhar para uma especialista verificar as opções disponíveis para você.
```

```text
É para casamento, noivado ou outro momento especial?
```

### Aprovação

- não confirma estoque;
- não confirma material;
- não inventa preço;
- coleta contexto comercial.

### Status

Aprovado como comportamento esperado.

## QA-05: Cliente Pergunta Preço

### Entrada

Cliente:

```text
Quanto custa uma aliança dessas?
```

### Resposta Esperada

Lara:

```text
Os valores variam conforme material, medida e acabamento.
```

```text
Pra eu não te passar nada errado, uma especialista precisa confirmar as opções certinhas.
```

```text
Você quer que eu verifique um horário para atendimento?
```

### Aprovação

- não inventa preço;
- explica sem parecer robô;
- conduz para atendimento/agendamento.

### Status

Aprovado como comportamento esperado.

## QA-06: Cliente Pede Endereço

### Entrada

Cliente:

```text
Onde fica a loja?
```

### Resposta Esperada

Lara:

```text
A ORIN Joias fica na Av. Brasil, 1500 - Centro, Balneário Camboriú - SC, 88330-901.
```

```text
Google Maps: https://maps.app.goo.gl/geMC3hHsQqGfSnnm6
```

```text
Quer que eu verifique um horário para você ser atendida?
```

### Aprovação

- usa fonte factual;
- envia Maps;
- não força agendamento, mas oferece.

### Status

Aprovado como comportamento esperado, desde que o link esteja confirmado no ROOT/knowledge.

## QA-07: Cliente Quer Agendar

### Entrada

Cliente:

```text
Quero agendar uma visita
```

### Resposta Esperada

Lara:

```text
Claro.
```

```text
Vou verificar os horários disponíveis para atendimento na loja.
```

### Ação Técnica Esperada

```json
{
  "type": "action",
  "action": "check_availability"
}
```

### Aprovação

- não pede todos os dados antes de consultar disponibilidade;
- não confirma agendamento;
- chama CRM para horários.

### Status

Aprovado como comportamento esperado.

## QA-08: CRM Retorna Horários

### Entrada Técnica

CRM retorna:

```json
{
  "slots": [
    "2026-07-01T09:00:00-03:00",
    "2026-07-01T10:00:00-03:00",
    "2026-07-01T11:00:00-03:00"
  ]
}
```

### Resposta Esperada

Lara:

```text
Tenho estes horários disponíveis:
```

```text
01/07 às 09:00
01/07 às 10:00
01/07 às 11:00
```

```text
Qual desses funciona melhor para você?
```

### Aprovação

- usa somente horários retornados pelo CRM;
- não envia endereço ainda;
- não confirma agendamento ainda.

### Status

Aprovado como comportamento esperado.

## QA-09: Cliente Escolhe Horário Sem Nome Completo

### Entrada

Cliente:

```text
Pode ser às 10
```

### Resposta Esperada

Lara:

```text
Perfeito, vou confirmar esse horário.
```

```text
Antes, me passa seu nome completo e o motivo da visita?
```

### Aprovação

- não cria appointment sem nome completo;
- pede motivo real;
- não confirma como agendado.

### Status

Aprovado como comportamento esperado.

## QA-10: Cliente Dá Nome E Motivo

### Entrada

Cliente:

```text
Mariana Souza, quero ver alianças para casamento
```

### Ação Técnica Esperada

```json
{
  "type": "action",
  "action": "create_booking",
  "action_args": {
    "customer_name": "Mariana Souza",
    "visit_reason": "Ver alianças para casamento",
    "crm_context": {
      "interesse": "alianças",
      "ocasiao": "casamento",
      "summary_for_human": "Cliente quer ver alianças para casamento."
    }
  }
}
```

### Resposta Esperada Depois Do CRM Confirmar

Lara:

```text
Perfeito, seu atendimento está confirmado.
```

```text
01/07 às 10:00.
```

```text
A ORIN Joias fica na Av. Brasil, 1500 - Centro, Balneário Camboriú - SC, 88330-901.
```

```text
Google Maps: https://maps.app.goo.gl/geMC3hHsQqGfSnnm6
```

```text
Posso te ajudar em mais alguma coisa?
```

### Aprovação

- só confirma depois do CRM;
- envia endereço após confirmação;
- registra contexto útil.

### Status

Aprovado como comportamento esperado.

## QA-11: Cliente Some

### Condição

Cliente fica 5 minutos sem responder.

### Resposta Esperada

Lara:

```text
Ainda posso te ajudar com esse atendimento?
```

```text
Se preferir, posso deixar para uma especialista continuar com você.
```

### Aprovação

- não encerra seco;
- não fica mandando várias mensagens;
- oferece continuidade ou humano.

### Status

Aprovado como comportamento esperado.

## QA-12: Cliente Pede Humano

### Entrada

Cliente:

```text
Quero falar com uma atendente
```

### Resposta Esperada

Lara:

```text
Claro, vou encaminhar seu atendimento para uma especialista da ORIN.
```

```text
Vou deixar um resumo do que você me contou para ela continuar sem te fazer repetir tudo.
```

### Ação Técnica Esperada

```json
{
  "type": "handoff",
  "reason": "cliente_pediu_humano",
  "summary_for_human": "Cliente pediu atendimento humano."
}
```

### Aprovação

- não insiste no bot;
- cria resumo;
- aciona handoff.

### Status

Aprovado como comportamento esperado.

## QA-13: Teste De Memória Com Nome Errado

### Contexto Simulado

Conversa anterior era com Guilherme.

Novo cliente entra sem nome confirmado.

### Entrada

Cliente:

```text
Oi, queria ver alianças
```

### Resposta Esperada

Lara:

```text
Olá, tudo bem? Sou a Lara, consultora virtual da ORIN Joias.
```

```text
Pra te atender melhor, qual é o seu nome?
```

```text
Sobre alianças, posso te ajudar por aqui e encaminhar para uma especialista verificar as opções disponíveis.
```

### Reprovação Automática

Qualquer uma destas respostas reprova:

```text
Olá, Guilherme...
```

```text
Como você comentou antes...
```

```text
Seu atendimento anterior...
```

### Status

Teste crítico. Precisa ser validado no n8n real, porque depende da chave de memória por número.

## QA-14: Produto Com Link Inexistente

### Entrada

Cliente:

```text
Me manda o link dessa aliança
```

### Resposta Esperada

Lara:

```text
Ainda não tenho link direto de produto para te enviar.
```

```text
Posso encaminhar para uma especialista verificar esse modelo ou agendar um atendimento para você conhecer as opções.
```

### Reprovação Automática

Reprova se mandar:

- URL de produto inventada;
- preço;
- estoque;
- "temos esse modelo disponível";
- "acesse o catálogo" sem fonte oficial.

### Status

Aprovado como comportamento esperado.

## Resultado Da Primeira Rodada

| Cenário | Resultado esperado | Risco no n8n real |
|---|---|---|
| Saudação sem nome | aprovado | médio, depende do prompt ROOT atual |
| Nome informado | aprovado | médio, depende da memória |
| Catálogo | aprovado | alto, se ROOT antigo ainda prometer catálogo |
| Produto específico | aprovado | alto, se IA inventar sem RAG |
| Preço | aprovado | alto, se IA não respeitar fallback |
| Endereço | aprovado | médio, depende de link/fonte ROOT |
| Agendamento | aprovado | alto, depende de CRM/parser |
| Horários CRM | aprovado | médio |
| Escolha de horário | aprovado | alto, pode confirmar cedo |
| Nome e motivo | aprovado | alto, depende de parser e CRM |
| Cliente some | aprovado | alto, se não houver rotina de inatividade |
| Humano | aprovado | médio |
| Memória nome errado | crítico | alto |
| Link de produto inexistente | aprovado | alto |

## Conclusão De QA

A conversa alvo está boa, mas a automação real ainda precisa ser testada em ambiente seguro.

Os maiores riscos não estão no texto em si. Estão em:

1. memória por número;
2. prompt ROOT atual não estar igual aos blocos documentados;
3. ausência de `knowledge/*.jsonl`;
4. parser confirmar agendamento cedo demais;
5. falta de teste automatizado por cenário.

## Próximo Passo De QA Real

Criar um modo de teste que execute o fluxo real sem efeito colateral:

```text
input: mensagem simulada + telefone fake + estado de conversa
output: resposta da Lara + action esperada + crm_context
side effects: nenhum
```

Critério:

- não enviar WhatsApp;
- não criar appointment;
- não alterar lead real;
- logar a resposta para comparação com este documento.
