# SPEC: Regras De Validacao E Negocio - Lara V9

> Spec e contrato do que deve ser construido. Nao e PR, nao e task.

## Status
Em revisao

## Contexto
Regras transversais da Lara V9 Shadow SDR.

Estas regras existem para impedir os erros reais ja observados:

- `/rest` cair em modo livre;
- `/reset` apagar configuracao sem confirmacao forte;
- `Meu nome e Guilherme` virar `Perfeito, Meu`;
- saudacao virar nome;
- repeticao de abertura;
- confirmacao de agenda sem dados;
- resposta factual sem fonte;
- memoria misturada entre contatos.

## Regras de negocio

- **RN-01: Comando ROOT desconhecido nao entra em modo livre.**
  - Condicao / gatilho: mensagem comeca com `/` em sessao ROOT ativa.
  - Resultado esperado: se comando nao existe no mapa, responder erro deterministico.
  - Excecoes: N/A.

- **RN-02: `/reset` e destrutivo e exige confirmacao forte.**
  - Condicao / gatilho: admin envia `/reset`.
  - Resultado esperado: salvar pending action e pedir `CONFIRMAR RESET`.
  - Excecoes: reset real so executa quando a proxima mensagem for exatamente `CONFIRMAR RESET`.

- **RN-02A: ROOT Console altera configuracao por draft versionado.**
  - Condicao / gatilho: admin altera prompt, bloco, regra, link, catalogo, persona, tom ou comportamento.
  - Resultado esperado: criar rascunho, mostrar previa/diff, pedir confirmacao, salvar nova versao e registrar audit log.
  - Excecoes: comandos somente leitura como `/status`, `/help`, `/log` nao exigem draft.

- **RN-02B: `/assumir` pausa a Lara para atendimento humano.**
  - Condicao / gatilho: admin autorizado envia `/assumir [numero]` ou aciona assumir dentro do contexto de uma conversa.
  - Resultado esperado: marcar `human_takeover=true` para o numero alvo; Lara nao responde mais aquele cliente; mensagens continuam sendo logadas.
  - Excecoes: nenhuma em producao.

- **RN-02C: `/devolver` reativa a Lara para a conversa.**
  - Condicao / gatilho: admin autorizado envia `/devolver [numero]` ou `/bot [numero]`.
  - Resultado esperado: marcar `human_takeover=false`; Lara volta a responder a partir do estado atualizado.
  - Excecoes: se houver dados sensiveis, estado inconsistente ou cliente irritado, exigir handoff/humano manual.

- **RN-03: Nome de perfil do WhatsApp nao e nome confirmado.**
  - Condicao / gatilho: webhook traz `profile_name`.
  - Resultado esperado: perfil pode ser contexto fraco, mas nunca saudacao pelo nome nem `confirmed_name`.
  - Excecoes: cliente confirma explicitamente que aquele e o nome.

- **RN-04: Saudacao nao vira nome.**
  - Condicao / gatilho: mensagem como `oi`, `ola`, `olá`, `bom dia`, `boa tarde`, `boa noite`, `ok`, `sim`, `obg`.
  - Resultado esperado: Lara se apresenta e pergunta nome se ainda faltar.
  - Excecoes: N/A.

- **RN-05: Frase de apresentacao deve extrair o nome real.**
  - Condicao / gatilho: mensagens como `meu nome e X`, `me chamo X`, `sou X`, `aqui e X`, `pode me chamar de X`.
  - Resultado esperado: extrair apenas `X`, normalizar capitalizacao e salvar `confirmed_name`.
  - Excecoes: se `X` for vazio, generico ou comando, pedir nome novamente.

- **RN-06: Primeiro nome isolado pode confirmar nome apenas no estado correto.**
  - Condicao / gatilho: cliente responde uma palavra apos a Lara perguntar nome.
  - Resultado esperado: salvar como `confirmed_name` e avancar para descoberta.
  - Excecoes: bloquear palavras de saudacao, horarios, comandos, confirmacoes curtas e termos genericos.

- **RN-07: Abertura roda uma vez por conversa ativa.**
  - Condicao / gatilho: `confirmed_name` ja existe ou estado nao e `inicio/identificacao`.
  - Resultado esperado: nao repetir apresentacao inicial.
  - Excecoes: `/reset`, expirar sessao ou reinicio explicito.

- **RN-08: Supervisor escolhe agente por estado e intencao.**
  - Condicao / gatilho: toda mensagem de cliente nao ROOT.
  - Resultado esperado: selecionar exatamente um agente principal.
  - Excecoes: se ambiguo, usar `Agent Discovery` ou `Agent Handoff`.

- **RN-09: Fatos exigem fonte.**
  - Condicao / gatilho: cliente pede endereco, catalogo, politica, prazo, preco, produto, estoque, material ou link.
  - Resultado esperado: consultar fonte factual configurada ou escalar/avisar que vai confirmar.
  - Excecoes: endereco oficial pode ficar em config versionada enquanto nao houver RAG completo.

- **RN-10: IA nao inventa preco, estoque, prazo, material, desconto ou disponibilidade.**
  - Condicao / gatilho: qualquer resposta sobre dado comercial factual.
  - Resultado esperado: responder com limite e conduzir para especialista/agendamento quando faltar fonte.
  - Excecoes: N/A.

- **RN-11: Agenda real vem somente do CRM.**
  - Condicao / gatilho: cliente pede horario, visita ou agendamento.
  - Resultado esperado: usar `check_availability`.
  - Excecoes: QA/shadow usa mock controlado marcado como `qa_mode=true`.

- **RN-12: Appointment exige dados minimos.**
  - Condicao / gatilho: tentativa de `create_appointment`.
  - Resultado esperado: bloquear se faltar nome confirmado, telefone, data/hora, motivo da visita e confirmacao.
  - Excecoes: e-mail so e obrigatorio se CRM exigir.

- **RN-13: Motivo da visita deve ser util para atendente.**
  - Condicao / gatilho: antes de criar appointment.
  - Resultado esperado: coletar interesse, ocasiao e resumo minimo.
  - Excecoes: se cliente se recusar, escalar para humano ou registrar recusa.

- **RN-14: Confirmacao antes de criar appointment.**
  - Condicao / gatilho: dados minimos preenchidos.
  - Resultado esperado: Lara resume e pede confirmacao do cliente.
  - Excecoes: nenhuma em producao.

- **RN-15: Modo QA/shadow nao tem side effects.**
  - Condicao / gatilho: payload `qa_mode=true` ou workflow shadow.
  - Resultado esperado: nao enviar WhatsApp real, nao criar appointment real, nao atualizar CRM real.
  - Excecoes: N/A. O numero de producao do cliente `+55 47 9696-3593` nao deve ser usado para QA destrutivo.

- **RN-16: Validador P0 bloqueia resposta antes do envio.**
  - Condicao / gatilho: toda resposta gerada por agente/LLM.
  - Resultado esperado: se violar regra P0, enviar fallback seguro ou pedir humano.
  - Excecoes: N/A.

## Regras de validacao de entrada

- `message`
  - obrigatorio;
  - string;
  - trim antes de processar;
  - preservar original para auditoria.

- `whatsapp_number`
  - obrigatorio;
  - normalizar para E.164 ou formato canonico interno;
  - nunca depender de nome do contato para chave de memoria.

- `profile_name`
  - opcional;
  - nao confiavel;
  - nunca vira `confirmed_name` sozinho.

- `confirmed_name`
  - minimo 2 caracteres;
  - nao pode estar na lista de bloqueio;
  - pode ser primeiro nome para conversa, mas CRM pode exigir nome completo antes de appointment.

- `root_command`
  - se comeca com `/`, deve bater em comando permitido ou virar erro controlado.

- `human_takeover`
  - boolean;
  - quando `true`, o fluxo de cliente nao pode chamar LLM nem enviar resposta automatica;
  - deve registrar quem assumiu e quando.

- `appointment`
  - `starts_at` e `ends_at` em ISO8601 com timezone;
  - `visit_reason` minimo 8 caracteres e nao generico;
  - `customer_name` obrigatorio;
  - `phone_confirmed` obrigatorio antes de criacao real.

## Mensagens

- Comando desconhecido:
  - `Comando nao reconhecido.`
  - `Voce quis dizer /reset?`
  - `Use /help para ver os comandos disponiveis.`

- Reset pendente:
  - `Atencao: /reset apaga toda a configuracao atual da Lara.`
  - `Para confirmar, responda exatamente: CONFIRMAR RESET`
  - `Para cancelar, responda: cancelar`

- Reset cancelado:
  - `Reset cancelado. Nenhuma configuracao foi alterada.`

- Assumir conversa:
  - `Atendimento assumido. A Lara esta pausada para este cliente.`

- Devolver conversa:
  - `Atendimento devolvido para a Lara.`

- Nome invalido:
  - `Nao consegui identificar seu nome com seguranca. Como posso te chamar?`

- Falta motivo de visita:
  - `Perfeito. Para deixar o atendimento mais assertivo, me conta qual assunto voce gostaria de tratar na loja?`

## Camada de aplicacao

- **Banco**
  - estado duravel por numero;
  - audit log de ROOT;
  - logs de decisao.

- **API/Backend**
  - parser deterministico;
  - validador P0;
  - contrato de ferramentas;
  - bloqueio de side effects em QA.

- **Frontend/UI**
  - N/A nesta fase.

## Casos de borda
- `/rest`, `/reste`, `/resete`.
- `/reset` seguido de `sim`, que deve cancelar/nao executar se a regra exigir `CONFIRMAR RESET`.
- `Meu nome e Guilherme`.
- `me chamo Ana Paula`.
- `sou o Guilherme`.
- `boa noite`.
- `Pode ser as 10`.
- `Ok`.
- cliente manda audio/imagem/documento.
- duas mensagens rapidas no buffer.
- mesmo cliente volta depois de sessao expirada.
- dois numeros diferentes com mesmo nome.

## Testes
- Unit de parser ROOT.
- Unit de `/assumir` e `/devolver`.
- Unit de extrator de nome.
- Unit de state transition.
- Unit de validador P0.
- Integração shadow para jornada de abertura.
- Integração shadow para jornada de agendamento.
- Integração shadow para ROOT.
- QA remoto em numero de teste antes de qualquer swap de producao.

## Seguranca
- ROOT so para numeros autorizados.
- Logs com dados sensiveis minimizados.
- LLM output tratado como nao confiavel.
- Tools com side effect atras de validacao deterministica.
- QA/shadow sem side effects.
- Numero de producao do cliente: `+55 47 9696-3593`. Testes destrutivos, reset, troca de config e automacoes experimentais devem rodar em numero de teste ou modo shadow.

## Riscos
- Lista de bloqueio de nomes pode bloquear nome real incomum se for agressiva demais.
- Confirmacao forte de reset pode confundir usuario admin, mas e necessaria por seguranca.
- State machine muito rigida pode parecer robotica se nao tiver fallback bem escrito.
- Sem memoria duravel, o erro volta em restart/expiracao.

## Decisoes pendentes
1. Lista final de numeros ROOT autorizados.
2. E-mail sera obrigatorio no appointment ou apenas desejavel?
3. Fonte oficial do catalogo.
4. Onde persistir estado duravel.
5. Qual numero de teste oficial substitui o numero de producao durante QA?

## Criterios de aceite
- Todas as RN P0 tem teste automatizado.
- Nenhuma resposta e enviada sem passar pelo validador P0.
- `/rest` nao altera configuracao.
- `/reset` nao apaga sem `CONFIRMAR RESET`.
- `/assumir` pausa resposta automatica para o cliente alvo.
- `/devolver` reativa resposta automatica para o cliente alvo.
- `Meu nome e Guilherme` salva `Guilherme`.
- QA/shadow nao gera side effects.
