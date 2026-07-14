#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const scenariosPath = path.join(root, 'qa', 'lara_qa_scenarios.json');
const defaultActualPath = path.join(root, 'qa', 'lara_actual_outputs.json');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function flattenText(output) {
  if (!output) return '';
  const blocks = Array.isArray(output.message_blocks) ? output.message_blocks : [];
  return [
    output.type || '',
    output.action || '',
    output.reason || '',
    ...blocks,
    JSON.stringify(output.action_args || {}),
    JSON.stringify(output.crm_context || {})
  ].join('\n');
}

function normalize(s) {
  return String(s || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

function includesPattern(text, pattern) {
  return normalize(text).includes(normalize(pattern));
}

function regexHits(text, pattern) {
  try {
    return new RegExp(pattern, 'i').test(text);
  } catch {
    return includesPattern(text, pattern);
  }
}

function validateJsonl(filePath) {
  const lines = fs.readFileSync(filePath, 'utf8').split(/\r?\n/).filter(Boolean);
  const errors = [];
  lines.forEach((line, index) => {
    try {
      const parsed = JSON.parse(line);
      for (const key of ['id', 'source', 'type', 'confidence', 'updated_at']) {
        if (!Object.prototype.hasOwnProperty.call(parsed, key)) {
          errors.push(`${filePath}:${index + 1} missing ${key}`);
        }
      }
    } catch (err) {
      errors.push(`${filePath}:${index + 1} invalid JSON: ${err.message}`);
    }
  });
  return errors;
}

function loadActualOutputs(actualPath, scenarios) {
  if (actualPath) {
    if (!fs.existsSync(actualPath)) {
      throw new Error(`Actual outputs file not found: ${actualPath}`);
    }
    const actual = readJson(actualPath);
    return actual.outputs || actual;
  }

  const outputs = {};
  for (const scenario of scenarios) {
    outputs[scenario.id] = scenario.expected;
  }
  return outputs;
}

function validateScenario(scenario, actual, globalForbidden) {
  const errors = [];
  const text = flattenText(actual);

  if (!actual) {
    return [`${scenario.id}: missing actual output`];
  }

  if (scenario.expected.type && actual.type !== scenario.expected.type) {
    errors.push(`${scenario.id}: expected type ${scenario.expected.type}, got ${actual.type}`);
  }

  if (scenario.expected.action && actual.action !== scenario.expected.action) {
    errors.push(`${scenario.id}: expected action ${scenario.expected.action}, got ${actual.action}`);
  }

  const required = scenario.required_patterns || [];
  for (const pattern of required) {
    if (!includesPattern(text, pattern)) {
      errors.push(`${scenario.id}: missing required pattern "${pattern}"`);
    }
  }

  const forbidden = [...globalForbidden, ...(scenario.forbidden_patterns || [])];
  for (const pattern of forbidden) {
    if (regexHits(text, pattern)) {
      errors.push(`${scenario.id}: forbidden pattern hit "${pattern}"`);
    }
  }

  const blocks = Array.isArray(actual.message_blocks) ? actual.message_blocks : [];
  if (['response', 'post_action_response', 'handoff'].includes(actual.type) && blocks.length === 0) {
    errors.push(`${scenario.id}: response has no message_blocks`);
  }
  if (scenario.expected?.min_message_blocks && blocks.length < scenario.expected.min_message_blocks) {
    errors.push(`${scenario.id}: expected at least ${scenario.expected.min_message_blocks} message_blocks, got ${blocks.length}`);
  }

  for (const [index, block] of blocks.entries()) {
    if (String(block).length > 240) {
      errors.push(`${scenario.id}: block ${index + 1} too long (${String(block).length} chars)`);
    }
  }

  if (scenario.id === 'QA-10' && scenario.expected?.action === 'create_booking') {
    const args = actual.action_args || {};
    if (!args.customer_name || String(args.customer_name).trim().split(/\s+/).length < 2) {
      errors.push(`${scenario.id}: create_booking missing full customer_name`);
    }
    if (!args.visit_reason || String(args.visit_reason).trim().length < 8) {
      errors.push(`${scenario.id}: create_booking missing real visit_reason`);
    }
  }

  return errors;
}

function main() {
  const actualArgIndex = process.argv.indexOf('--actual');
  const idsArgIndex = process.argv.indexOf('--ids');
  const allowPartial = process.argv.includes('--allow-partial');
  const actualPath = actualArgIndex >= 0 ? path.resolve(process.argv[actualArgIndex + 1]) : null;
  const selectedIds = idsArgIndex >= 0
    ? new Set(process.argv[idsArgIndex + 1].split(',').map((value) => value.trim()).filter(Boolean))
    : null;
  const scenariosDoc = readJson(scenariosPath);
  const scenarios = (scenariosDoc.scenarios || []).filter((scenario) => !selectedIds || selectedIds.has(scenario.id));
  const outputs = loadActualOutputs(actualPath, scenarios);

  const knowledgeDir = path.join(root, 'knowledge');
  const jsonlFiles = fs.readdirSync(knowledgeDir)
    .filter((file) => file.endsWith('.jsonl'))
    .map((file) => path.join(knowledgeDir, file));

  const jsonlErrors = jsonlFiles.flatMap(validateJsonl);
  const scenarioResults = [];

  for (const scenario of scenarios) {
    if (allowPartial && !outputs[scenario.id]) {
      continue;
    }
    const errors = validateScenario(scenario, outputs[scenario.id], scenariosDoc.global_forbidden_patterns || []);
    scenarioResults.push({ id: scenario.id, title: scenario.title, ok: errors.length === 0, errors });
  }

  const failed = scenarioResults.filter((result) => !result.ok);
  const report = {
    generated_at: new Date().toISOString(),
    mode: actualPath ? 'actual_outputs' : 'expected_fixture',
    actual_path: actualPath || null,
    knowledge_files: jsonlFiles.map((file) => path.relative(root, file)),
    jsonl_ok: jsonlErrors.length === 0,
    jsonl_errors: jsonlErrors,
    total_scenarios: scenarioResults.length,
    total_scenarios_available: scenarios.length,
    allow_partial: allowPartial,
    passed: scenarioResults.length - failed.length,
    failed: failed.length,
    results: scenarioResults
  };

  const reportPath = path.join(root, 'qa', 'lara_qa_report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');

  console.log(`QA mode: ${report.mode}`);
  console.log(`Knowledge JSONL: ${report.jsonl_ok ? 'OK' : 'FAIL'}`);
  console.log(`Scenarios: ${report.passed}/${report.total_scenarios} passed`);
  console.log(`Report: ${path.relative(root, reportPath)}`);

  if (jsonlErrors.length > 0 || failed.length > 0) {
    for (const error of jsonlErrors) console.error(error);
    for (const result of failed) {
      for (const error of result.errors) console.error(error);
    }
    process.exit(1);
  }
}

main();
