# Benchmark Dos Fluxos SDR De Referencia

Data: 2026-07-09

## Resumo

Os repositórios de referência não provam que basta trocar prompt. Eles provam o contrário: atendimento confiável precisa de estado, contrato de saída, memória isolada, roteamento e validação antes de enviar mensagem.

Repositórios analisados localmente:

- `reference-repos/sdr-evolufit`, commit `ab5fd6d`;
- `reference-repos/Sistema-SDR-Multiagentes`, commit `b992f40`.

## Critério Do Teste

O teste não é copiar texto dos bots.

O teste é comparar arquitetura contra bugs reais da Lara:

- nome extraído errado, exemplo: `Meu nome é Guilherme` virando `Perfeito, Meu`;
- comando ROOT desconhecido, exemplo: `/rest`, caindo em modo livre;
- reset destrutivo sem confirmação forte;
- saudação repetida depois de nome informado;
- agendamento sem dados mínimos;
- resposta factual sem fonte;
- memória misturada entre contatos.

## O Que O EvoluFit Faz Melhor

Arquivo principal:

- `reference-repos/sdr-evolufit/prompts/sdr-claude-prompt.md`

Pontos técnicos:

- força resposta em JSON válido;
- separa `resposta`, `temperatura`, `acao`, `objetivo_detectado` e `resumo_qualificacao`;
- busca lead e histórico antes da IA;
- limita histórico às últimas 10 mensagens;
- salva mensagem recebida, mensagem enviada e atualização do lead;
- tem workflow separado para follow-up.

Limite:

- é linear e simples. Não resolve sozinho ROOT, agenda, CRM, catálogo, WhatsApp premium e múltiplos estados da Lara.

Lição aplicável:

```text
Toda resposta da Lara precisa sair com contrato estruturado e validação, não só texto.
```

## O Que O Multiagentes Faz Melhor

Arquivos principais:

- `reference-repos/Sistema-SDR-Multiagentes/prompts/system-messages/agente-supervisor.md`;
- `reference-repos/Sistema-SDR-Multiagentes/prompts/system-messages/agente-geral.md`;
- `reference-repos/Sistema-SDR-Multiagentes/workflows/principal/whatsapp-sara.json`;
- `reference-repos/Sistema-SDR-Multiagentes/workflows/agentes/agente-supervisor.json`;
- `reference-repos/Sistema-SDR-Multiagentes/workflows/agentes/agente-geral.json`;
- `reference-repos/Sistema-SDR-Multiagentes/workflows/agentes/agente-loteamentos.json`;
- `reference-repos/Sistema-SDR-Multiagentes/workflows/agentes/agente-construtora.json`.

Pontos técnicos:

- tem agente supervisor;
- exige `Think_tool` antes de rotear;
- tem agente geral para saudação, nome e triagem;
- mantém memória PostgreSQL compartilhada;
- usa agentes especialistas com escopo limitado;
- especialistas usam RAG/Supabase para fatos;
- ferramentas registram lead, anotação e interesse;
- fallback é explícito: em dúvida, vai para agente geral.

Limite:

- é mais pesado. Copiar literalmente para a ORIN criaria complexidade e dependências desnecessárias.

Lição aplicável:

```text
A Lara precisa de supervisor/roteador e estado explícito, mesmo que continue dentro do n8n.
```

## Onde A Lara Está Inferior Hoje

### 1. Comandos ROOT

Problema visto:

```text
/rest -> "Nenhuma alteração foi identificada na instrução."
```

Causa:

- o parser permite comando com barra desconhecido cair em `modo_livre`;
- comando administrativo ficou dependente de interpretação da IA.

Correção necessária:

- se começa com `/` e não existe no mapa, responder erro determinístico;
- `/reset` precisa de confirmação forte antes de apagar;
- `/rest`, `/reste`, `/resete` não podem alterar nada.

Evidência local em 2026-07-09, executando o próprio node `ROOT: Parser de Comando` do workflow:

```json
{
  "input": "/rest",
  "session_active": true,
  "output": {
    "command": "modo_livre",
    "args": "/rest",
    "raw": "/rest",
    "session_active": true
  }
}
```

Conclusão:

```text
Bug confirmado. O parser do ROOT está errado.
```

### 2. Extração De Nome

Problema visto:

```text
Cliente: Meu nome é Guilherme
Lara: Perfeito, Meu.
```

Causa:

- parser/guard trata primeira palavra como nome;
- falta extrator determinístico para padrões de apresentação.

Correção necessária:

- reconhecer padrões:
  - `meu nome é X`;
  - `me chamo X`;
  - `sou X`;
  - `aqui é X`;
  - `pode me chamar de X`;
- bloquear palavras inválidas como nome: `meu`, `minha`, `nome`, `oi`, `olá`, `ok`, `sim`, horarios e comandos.

Evidência local em 2026-07-09, executando o próprio node `Code: Parse Agent Output` do workflow:

```json
{
  "input": "Meu nome é Guilherme",
  "output": {
    "message_blocks": [
      "Perfeito, Meu.",
      "Me conta o que você está buscando hoje?",
      "Se quiser, posso te mostrar nosso catálogo de joias ou podemos agendar um atendimento presencial. Qual você prefere?"
    ],
    "crm_context": {
      "customer_name": "Meu nome"
    },
    "block_reason": "full_name_detected"
  }
}
```

Conclusão:

```text
Bug confirmado. A extração de nome está errada para frases naturais de apresentação.
```

### 3. Estado De Conversa

Problema:

- a Lara ainda decide muita coisa pela mensagem atual e pelo histórico textual.

Correção necessária:

- manter estado explícito por número:
  - `inicio`;
  - `identificacao`;
  - `descoberta`;
  - `catalogo`;
  - `agenda_slots`;
  - `agenda_contexto`;
  - `agenda_confirmacao`;
  - `agenda_confirmado`;
  - `handoff`.

### 4. QA Insuficiente

Problema:

- testes de frase passam, conversa real quebra.

Correção necessária:

- QA por jornada, validando transição de estado a cada mensagem;
- testes novos adicionados:
  - `QA-21`: `Meu nome é Guilherme` deve virar `Perfeito, Guilherme`;
  - `QA-22`: `/rest` deve responder comando desconhecido e não cair em modo livre.

## Matriz De Benchmark

| Item | EvoluFit | Multiagentes | Lara atual | Decisão |
|---|---|---|---|---|
| Contrato JSON | Sim | Sim, via agentes/tools | Parcial | reforçar |
| Memória isolada | Sheets por telefone | PostgreSQL por sessão | Redis por número, mas estado fraco | manter Redis e adicionar state |
| Supervisor | Não | Sim | Não explícito | criar supervisor lógico |
| Agente de abertura | Prompt linear | Agente geral | Misturado no prompt/guard | separar |
| RAG/fatos | Não robusto | Supabase Vector | JSONL local planejado | implementar busca obrigatória |
| ROOT admin | Não existe | Não existe | Existe, mas frágil | travar comandos |
| Reset seguro | Não aplicável | Não aplicável | Falhou | confirmação forte |
| QA conversacional | Fraco | Fraco/moderado | Local parcial | ampliar por jornada |

## Plano De Teste Antes De Produção

### Bateria P0

1. `/rest`
   - esperado: comando não reconhecido;
   - proibido: modo livre, alteração, reset.

2. `/reset`
   - esperado: pedir confirmação forte;
   - proibido: apagar direto.

3. `Meu nome é Guilherme`
   - esperado: `Perfeito, Guilherme`;
   - proibido: `Perfeito, Meu`.

4. `Boa noite`
   - esperado: pergunta nome;
   - proibido: tratar `Boa` como nome.

5. `Jhonatan`
   - esperado: avança para descoberta;
   - proibido: repetir saudação.

6. `quero agendar uma visita`
   - esperado: consultar horários ou coletar nome conforme estado;
   - proibido: confirmar sem CRM.

7. escolha de horário sem motivo
   - esperado: perguntar motivo;
   - proibido: criar appointment.

8. pedido de endereço
   - esperado: usar fonte oficial;
   - proibido: endereço antigo.

## Recomendação Técnica

Não trocar tudo por LangGraph agora.

Recomendação:

1. corrigir ROOT de forma determinística;
2. corrigir extrator de nome;
3. criar `State Controller` no n8n;
4. manter IA apenas para linguagem e interpretação de intenção;
5. bloquear envio se o contrato violar regra P0;
6. só depois avaliar LangGraph.

## Conclusão

A sua crítica procede: a Lara não está errando por falta de mais um prompt bonito. Ela está errando porque comandos, nome, estado e ações técnicas ainda não estão suficientemente determinísticos.

O que deve ser copiado dos repositórios é a disciplina arquitetural:

- contrato;
- memória;
- supervisor;
- ferramentas;
- fallback;
- QA.

O que não deve ser copiado:

- texto de venda;
- domínio;
- estrutura inteira;
- dependências desnecessárias.
