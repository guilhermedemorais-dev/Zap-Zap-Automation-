#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const backlogPath = path.join(root, 'qa', 'lara_execution_backlog.json');
const backlog = JSON.parse(fs.readFileSync(backlogPath, 'utf8'));
const tasks = backlog.tasks || [];

const order = {
  ready: 0,
  in_progress: -1,
  blocked_by_LARA: 1,
  blocked_by: 1,
  done: 9,
  future: 10,
  future_blocked: 11,
  future_optional: 12
};

function statusRank(status) {
  if (status === 'ready') return 0;
  if (status && status.startsWith('blocked')) return 1;
  if (status === 'done') return 9;
  if (status && status.startsWith('future')) return 10;
  return order[status] ?? 5;
}

function dependenciesDone(task) {
  const deps = task.dependencies || [];
  return deps.every((depId) => {
    const dep = tasks.find((candidate) => candidate.id === depId);
    return dep && dep.status === 'done';
  });
}

const done = tasks.filter((task) => task.status === 'done');
const inProgress = tasks.filter((task) => task.status === 'in_progress');
const ready = tasks.filter((task) => task.status === 'ready' || (task.status || '').startsWith('blocked') && dependenciesDone(task));
const blocked = tasks.filter((task) => (task.status || '').startsWith('blocked') && !dependenciesDone(task));
const future = tasks.filter((task) => (task.status || '').startsWith('future'));

ready.sort((a, b) => statusRank(a.status) - statusRank(b.status) || String(a.priority).localeCompare(String(b.priority)) || a.id.localeCompare(b.id));

console.log(`Projeto: ${backlog.project}`);
console.log(`Foco atual: ${backlog.current_focus}`);
console.log(`Concluidas: ${done.length}/${tasks.length}`);
console.log(`Em andamento: ${inProgress.length}`);
console.log(`Prontas: ${ready.length}`);
console.log(`Bloqueadas: ${blocked.length}`);
console.log(`Futuras: ${future.length}`);

if (inProgress.length > 0 || ready.length > 0) {
  const next = inProgress[0] || ready[0];
  console.log('');
  console.log(`${next.status === 'in_progress' ? 'Continuar' : 'Proxima acao'}: ${next.id} - ${next.title}`);
  console.log(`Prioridade: ${next.priority}`);
  console.log(`Tipo: ${next.type}`);
  if (next.docs && next.docs.length) console.log(`Docs: ${next.docs.join(', ')}`);
  if (next.acceptance && next.acceptance.length) {
    console.log('Criterios de aceite:');
    for (const item of next.acceptance) console.log(`- ${item}`);
  }
  if (next.remaining && next.remaining.length) {
    console.log('Restante:');
    for (const item of next.remaining) console.log(`- ${item}`);
  }
} else {
  console.log('');
  console.log('Nenhuma tarefa pronta. Revise bloqueios ou futuras.');
}
