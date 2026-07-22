# Issue: N8N - Lara V9 Shadow SDR

## Status
Discovery / SDD

## Prioridade
P0

## Labels sugeridas
`feature`, `high-priority`, `needs-info`

## Resumo
Criar a arquitetura e a task executavel da Lara V9 Shadow SDR, juntando as integracoes uteis da Lara atual com os padroes dos fluxos SDR de referencia: estado explicito, supervisor, agentes por responsabilidade, contrato JSON, memoria confiavel, validador P0 e QA real sem side effects.

## Numero de producao
Numero WhatsApp de producao do cliente:

`+55 47 9696-3593`

Esse numero nao deve ser usado para QA destrutivo, reset experimental ou teste com side effects. A V9 Shadow precisa de numero de teste oficial antes de execucao.

## Contexto
A Lara atual apresentou erros reais:

- `/rest` caiu em modo livre;
- `/reset` apagou configuracao sem confirmacao forte;
- `Meu nome e Guilherme` foi interpretado como `Perfeito, Meu`;
- testes locais anteriores nao garantiram comportamento em producao;
- agendamento e memoria ainda dependem demais de prompt/contexto solto.

Os repositorios de referencia indicam que o caminho correto nao e mais um prompt gigante, mas arquitetura com contrato, estado, supervisor, memoria e fallback.

## ROOT Console
O ROOT deve ser rebaixado para console seguro de configuracao:

- comandos determiniscos;
- alteracao de prompt/bloco/regra/link por draft;
- preview/diff antes de salvar;
- confirmacao obrigatoria;
- versionamento;
- audit log;
- rollback.

Comando destrutivo como `/reset` exige `CONFIRMAR RESET`.

## Takeover humano
Incluir funcao P0:

- `/assumir [numero]`: pausa a Lara para aquele cliente e permite atendimento humano;
- `/devolver [numero]` ou `/bot [numero]`: devolve a conversa para a Lara;
- durante takeover, a Lara nao responde automaticamente, mas continua registrando mensagens.

## Specs
- `docs/specs/lara-v9/module-spec.md`
- `docs/specs/lara-v9/validation-rules.md`
- `docs/specs/lara-v9/api.md`

## Task
- `docs/tasks/TASK-014-lara-v9-shadow-sdd.md`

## Criterios de aceite
- Specs revisadas.
- Decisoes pendentes mapeadas.
- V9 so sera implementada como shadow isolada.
- Producao nao sera alterada sem aprovacao.
- QA real devera validar `/rest`, `/reset`, `Meu nome e Guilherme`, saudacao, agendamento, motivo, confirmacao e side effects bloqueados.
- QA real devera validar `/assumir` e `/devolver`.

## Fora do escopo
- Implementar agora.
- Publicar em producao.
- Criar chat local.
- Criar catalogo online.

## Branch sugerida
`feat/lara-v9-shadow-sdr`
