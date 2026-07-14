#!/usr/bin/env node

const fs = require('fs');

const workflowPath = process.argv[2] || 'backups/n8n-ORION-WF-Bot-v7-with-address-name-loop-fix-draft-20260701.json';
const wf = JSON.parse(fs.readFileSync(workflowPath, 'utf8'));
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

function getNodeCode(name) {
  const node = wf.nodes.find((item) => item.name === name);
  if (!node) throw new Error(`Node not found: ${name}`);
  return node.parameters.jsCode;
}

function flatten(value) {
  if (!value) return '';
  const parts = [];
  if (value.type) parts.push(value.type);
  if (value.action) parts.push(value.action);
  if (Array.isArray(value.message_blocks)) parts.push(...value.message_blocks);
  if (value.response) parts.push(value.response);
  parts.push(JSON.stringify(value.crm_context || {}));
  parts.push(JSON.stringify(value.action_args || {}));
  return parts.join('\n');
}

function normalize(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

function assertIncludes(text, needle, label) {
  if (!normalize(text).includes(normalize(needle))) {
    throw new Error(`${label}: missing "${needle}"`);
  }
}

function assertNotIncludes(text, needle, label) {
  if (normalize(text).includes(normalize(needle))) {
    throw new Error(`${label}: forbidden "${needle}"`);
  }
}

async function runParserCase(test) {
  const code = getNodeCode('Code: Parse Agent Output');
  const fn = new AsyncFunction('$input', '$', '$items', code);
  const rawOutput = test.rawOutput || JSON.stringify({
    type: 'response',
    message_blocks: [
      'Olá, tudo bem?',
      'Sou a LARA, assistente da ORIN Joias.',
      'Para deixar seu atendimento mais personalizado, qual é o seu nome?'
    ],
    delay_seconds: 1,
    crm_context: {}
  });
  const contextText = test.contextText || 'NO_CONTEXT';
  const $input = { first: () => ({ json: { output: rawOutput } }) };
  const $ = (name) => ({
    first: () => ({ json: name === 'Get Message' ? { message: test.message } : { text: contextText } }),
    item: { json: name === 'Get Message' ? { message: test.message } : { text: contextText } }
  });
  const $items = () => [{ json: { message: test.message, text: contextText } }];
  const output = await fn($input, $, $items);
  return output[0].json;
}

async function runFinalBookingCase() {
  const code = getNodeCode('Code: Extrair Resposta Final');
  const fn = new AsyncFunction('$input', '$', code);
  const $input = { first: () => ({ json: { text: '{"type":"post_action_response","message_blocks":["ok"],"delay_seconds":1}' } }) };
  const $ = (name) => ({
    first: () => ({
      json: name === 'Code: Formatar Tool Result'
        ? { action_type: 'create_booking' }
        : { action_args: { starts_at: '2026-07-01T10:00:00-03:00' } }
    })
  });
  const output = await fn($input, $);
  return output[0].json;
}

async function main() {
  const tests = [
    {
      id: 'PARSER-01',
      message: 'Oii',
      must: ['Olá, tudo bem?', 'consultora virtual', 'informar seu nome'],
      mustNot: ['Prazer, Oii', 'customer_name']
    },
    {
      id: 'PARSER-02',
      message: 'Jhonatan',
      must: ['Perfeito, Jhonatan', 'catálogo de joias', 'atendimento presencial'],
      mustNot: ['qual é o seu nome', 'Sou a LARA']
    },
    {
      id: 'PARSER-03',
      message: 'jhonatan',
      must: ['Perfeito, Jhonatan', 'catálogo de joias', 'atendimento presencial'],
      mustNot: ['qual é o seu nome']
    },
    {
      id: 'PARSER-04',
      message: 'Jhonatam.',
      must: ['Perfeito, Jhonatam'],
      mustNot: ['qual é o seu nome']
    },
    {
      id: 'PARSER-05',
      message: '/exit',
      must: ['Olá, tudo bem'],
      mustNot: ['Prazer, /exit']
    },
    {
      id: 'PARSER-06',
      message: 'Pode ser às 10',
      rawOutput: JSON.stringify({ type: 'action', action: 'create_booking', arguments: {}, message_blocks: [], crm_context: {} }),
      must: ['Me confirma o dia', 'nome completo', 'motivo da visita'],
      mustNot: ['agendamento confirmado']
    },
    {
      id: 'PARSER-07',
      message: 'Ok',
      must: ['Olá, tudo bem?', 'consultora virtual', 'informar seu nome'],
      mustNot: ['Prazer, Ok']
    },
    {
      id: 'PARSER-08',
      message: 'Jhontan',
      must: ['Perfeito, Jhontan'],
      mustNot: ['qual é o seu nome']
    },
    {
      id: 'PARSER-09',
      message: 'endereco',
      must: ['Av. Brasil, 1500', '88330-901', 'Google Maps'],
      mustNot: ['Prazer, Endereco', 'Rua da Elegância', 'sala 316']
    },
    {
      id: 'PARSER-10',
      message: 'obg',
      must: ['Olá, tudo bem?', 'consultora virtual', 'informar seu nome'],
      mustNot: ['Prazer, Obg']
    },
    {
      id: 'PARSER-11',
      message: 'mariana souza',
      must: ['Perfeito, Mariana'],
      mustNot: ['qual é o seu nome']
    },
    {
      id: 'PARSER-12',
      message: 'Onde fica a loja?',
      must: ['Av. Brasil, 1500', '88330-901', 'Google Maps'],
      mustNot: ['Prazer, Onde', 'Rua da Elegância', 'sala 316', 'Hotel Sibara']
    },
    {
      id: 'PARSER-13',
      message: 'Boa noite',
      must: ['Olá, boa noite. Tudo bem?', 'consultora virtual', 'informar seu nome'],
      mustNot: ['Prazer, Boa', 'customer_name']
    },
    {
      id: 'PARSER-14',
      message: 'Bom dia',
      must: ['Olá, bom dia. Tudo bem?', 'consultora virtual', 'informar seu nome'],
      mustNot: ['Prazer, Bom', 'customer_name']
    },
    {
      id: 'PARSER-15',
      message: 'Boa tarde',
      must: ['Olá, boa tarde. Tudo bem?', 'consultora virtual', 'informar seu nome'],
      mustNot: ['Prazer, Boa', 'customer_name']
    }
  ];

  const results = [];
  for (const test of tests) {
    const output = await runParserCase(test);
    const text = flatten(output);
    for (const needle of test.must || []) assertIncludes(text, needle, test.id);
    for (const needle of test.mustNot || []) assertNotIncludes(text, needle, test.id);
    results.push({ id: test.id, ok: true });
  }

  const finalBooking = await runFinalBookingCase();
  const finalText = flatten(finalBooking);
  assertIncludes(finalText, 'Av. Brasil, 1500 - Centro, Balneário Camboriú - SC, 88330-901', 'FINAL-BOOKING');
  assertIncludes(finalText, 'Google Maps', 'FINAL-BOOKING');
  for (const forbidden of ['sala 316', 'Hotel Sibara', 'Rua das Flores', 'R. 101']) {
    assertNotIncludes(finalText, forbidden, 'FINAL-BOOKING');
  }
  results.push({ id: 'FINAL-BOOKING', ok: true });

  const workflowText = JSON.stringify(wf);
  for (const forbidden of ['Rua das Flores']) assertNotIncludes(workflowText, forbidden, 'WORKFLOW');

  console.log(`Workflow logic tests: ${results.length}/${results.length} passed`);
  for (const result of results) console.log(`${result.id}: OK`);
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
