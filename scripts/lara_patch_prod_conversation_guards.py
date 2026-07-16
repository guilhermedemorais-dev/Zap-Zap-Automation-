#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import time
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("N8N_BASE_URL", "https://n8n-zcac.srv1478933.hstgr.cloud").rstrip("/")
API_KEY = os.environ.get("N8N_API_KEY", "")
WORKFLOW_ID = os.environ.get("LARA_PROD_WORKFLOW_ID", "7SucjAi8zU69sQuT")
WEBHOOK_PATH = os.environ.get("LARA_PROD_WEBHOOK_PATH", "whatsapp-inbound")


CONVERSATION_GUARD = r"""
function normalizeNameForGuard(value) {
  return String(value || '')
    .trim()
    .replace(/[.!?]+$/g, '')
    .replace(/\s+/g, ' ');
}

function isInvalidCustomerName(value) {
  const text = normalizeNameForGuard(value);
  const first = text.split(/\s+/)[0] || '';
  const normalized = first.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const invalid = new Set([
    'tudo', 'tdo', 'sim', 'ok', 'okay', 'quero', 'queria', 'gostaria', 'pode',
    'meu', 'minha', 'filho', 'cara', 'irmao', 'irmão', 'ola', 'olá', 'oi',
    'bom', 'boa', 'noite', 'dia', 'tarde', 'perfeito', 'prazer', 'cliente',
    'lara', 'orin', 'agendar', 'agenda', 'atendimento', 'presencial', 'loja',
    'verificar', 'horario', 'horário', 'marcar'
  ]);
  if (!first || invalid.has(normalized)) return true;
  return !/^[A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]{2,30}$/.test(first);
}

function findConfirmedCustomerNameFromRuntime() {
  const source = runtimeHistoryTextForGuard();
  const parsedName = normalizeNameForGuard(parsed.crm_context?.customer_name || '');
  if (parsedName && !isInvalidCustomerName(parsedName)) return parsedName;

  const patterns = [
    /customer_name["']?\s*[:=]\s*["']([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+(?:[ \t]+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+){0,3})["']/,
    /\b(?:Client name|Nome do cliente|Cliente|Nome)\s*[:\-]\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+(?:[ \t]+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+){0,3})/i,
    /\b(?:Perfeito|Prazer|Olá|Ola),\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+(?:[ \t]+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+){0,3})\b/
  ];
  for (const pattern of patterns) {
    const match = source.match(pattern);
    if (!match) continue;
    const candidate = normalizeNameForGuard(match[1]);
    if (candidate && !isInvalidCustomerName(candidate)) return candidate;
  }
  return '';
}

function runtimeHistoryTextForGuard() {
  const rawParts = [contextText || ''];
  try { rawParts.push(String($('Get chat_history').first().json.history || '')); } catch(e) {}
  try {
    const raw = $('Get chat_history1').first().json.propertyName;
    rawParts.push(Array.isArray(raw) ? raw.join('\n') : String(raw || ''));
  } catch(e) {}
  return rawParts.filter(Boolean).join('\n');
}

function explicitNameFromMessage(value) {
  const text = normalizeNameForGuard(value);
  const match = text.match(/^\s*(?:meu\s+nome\s+(?:é|e)|me\s+chamo|sou\s+o|sou\s+a|aqui\s+(?:é|e))\s+([A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+(?:\s+[A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+){0,3})\b/i);
  if (!match) return '';
  const candidate = normalizeNameForGuard(match[1]);
  return candidate && !isInvalidCustomerName(candidate) ? candidate : '';
}

function tomorrowSaoPauloDate() {
  const now = new Date();
  const spNow = new Date(now.toLocaleString('en-US', { timeZone: 'America/Sao_Paulo' }));
  spNow.setDate(spNow.getDate() + 1);
  const yyyy = spNow.getFullYear();
  const mm = String(spNow.getMonth() + 1).padStart(2, '0');
  const dd = String(spNow.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function selectedAppointmentSlotFromText(value) {
  const text = String(value || '');
  const match = text.match(/\b(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?\s*(?:[-–—]|às|as)?\s*(\d{1,2})(?::(\d{2}))?\b/i);
  if (!match) return null;

  const now = new Date();
  const spNow = new Date(now.toLocaleString('en-US', { timeZone: 'America/Sao_Paulo' }));
  let year = match[3] ? Number(match[3]) : spNow.getFullYear();
  if (year < 100) year += 2000;

  const day = Number(match[1]);
  const month = Number(match[2]);
  const hour = Number(match[4]);
  const minute = match[5] ? Number(match[5]) : 0;
  if (day < 1 || day > 31 || month < 1 || month > 12 || hour < 0 || hour > 23 || minute < 0 || minute > 59) return null;

  const date = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  const time = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
  return {
    date,
    time,
    label: `${String(day).padStart(2, '0')}/${String(month).padStart(2, '0')} - ${time}`
  };
}

function selectedAppointmentSlotFromHistory(value) {
  const text = String(value || '').trim();
  const timeMatch = text.match(/^(?:pode ser\s*)?(?:às|as)?\s*(\d{1,2})(?::(\d{2}))?\s*(?:h|horas)?\s*$/i);
  if (!timeMatch) return null;
  const hour = String(Number(timeMatch[1])).padStart(2, '0');
  const minute = timeMatch[2] ? String(Number(timeMatch[2])).padStart(2, '0') : '00';
  const desiredTime = `${hour}:${minute}`;
  const source = runtimeHistoryTextForGuard();
  const slotPattern = /\b(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?\s*(?:[-–—]|às|as)?\s*(\d{1,2})(?::(\d{2}))?\b/gi;
  let match;
  while ((match = slotPattern.exec(source))) {
    const slotHour = String(Number(match[4])).padStart(2, '0');
    const slotMinute = match[5] ? String(Number(match[5])).padStart(2, '0') : '00';
    if (`${slotHour}:${slotMinute}` !== desiredTime) continue;
    return selectedAppointmentSlotFromText(`${match[1]}/${match[2]}${match[3] ? '/' + match[3] : ''} - ${desiredTime}`);
  }
  return null;
}

const appointmentIntentGuard = /(atendimento\s+presencial|agendar|agenda|visita|horário|horario|marcar|atendimento)/i.test(msg);
const askedNameAgainGuard = /(?:informar|dizer|me passa|me informe|qual (?:é|e))[^.!?\n]{0,80}\b(?:seu\s+)?nome\b|nome\?/i.test(responseText);
const historyTextGuard = runtimeHistoryTextForGuard();
const confirmedNameGuard = findConfirmedCustomerNameFromRuntime();
const explicitNameGuard = explicitNameFromMessage(userMessage);
const selectedSlotGuard = selectedAppointmentSlotFromText(userMessage) || selectedAppointmentSlotFromHistory(userMessage);
const askedForNameStageGuard = /(?:informar|dizer|me passa|me informe|qual (?:é|e))[^.!?\n]{0,80}\b(?:seu\s+)?nome\b|nome\?/i.test(historyTextGuard);
const offeredOptionsStageGuard = /(cat[aá]logo[\s\S]{0,160}atendimento presencial|Qual op[cç][aã]o voc[eê] prefere\?)/i.test(historyTextGuard);
const availabilityListedStageGuard = /(Tenho estes hor[aá]rios dispon[ií]veis|Qual desses hor[aá]rios funciona melhor)/i.test(historyTextGuard);
const askedVisitReasonStageGuard = /(motivo da visita|pe[cç]a que voc[eê] quer ver|assunto voc[eê] gostaria de tratar)/i.test(historyTextGuard);
const positiveShortAnswerGuard = /^(sim|ok|okay|pode|claro|isso|confirmo|perfeito|ta bom|tá bom|beleza|blz)$/i.test(msg);
const appointmentChoiceGuard = /(presencial|loja|atendimento|agenda|agendar|visita|marcar|hor[aá]rio|horario)/i.test(msg) || (offeredOptionsStageGuard && positiveShortAnswerGuard);
const usefulVisitReasonGuard = askedVisitReasonStageGuard && words(userMessage).length >= 3 && !selectedSlotGuard && !appointmentChoiceGuard;
const invalidParsedNameGuard = isInvalidCustomerName(parsed.crm_context?.customer_name || '') ? normalizeNameForGuard(parsed.crm_context?.customer_name || '') : '';
const responseTreatsInvalidNameGuard = /\b(?:Perfeito|Prazer|Olá|Ola),\s*(Tudo|Tdo|Sim|Ok|Okay|Quero|Gostaria|Meu|Filho|Agendar|Atendimento|Loja|Presencial)\b/i.test(responseText);
const likelyNamePromptAnswerWithoutName = (
  /\b(tudo|tdo|sim|ok|okay|quero|gostaria|pode|claro|meu filho|já disse|ja disse|agendar|atendimento|presencial|loja)\b/i.test(msg)
  && !confirmedNameGuard
  && !/^\s*(meu nome é|me chamo|sou o|sou a)\s+[A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]/i.test(userMessage)
);

if (confirmedNameGuard) {
  parsed.crm_context = { ...(parsed.crm_context || {}), customer_name: confirmedNameGuard };
}

if (parsed.type !== 'action' && parsed.type !== 'handoff' && explicitNameGuard) {
  const firstName = formatSingleName(explicitNameGuard.split(/\s+/)[0]);
  return [{
    json: {
      type: 'response',
      message_blocks: [
        `Perfeito, ${firstName}.`,
        'Me conta o que você está buscando hoje?',
        'Se quiser, posso te mostrar nosso catálogo de joias ou podemos agendar um atendimento presencial. Qual opção você prefere?'
      ],
      delay_seconds: 1,
      crm_context: { ...(parsed.crm_context || {}), customer_name: explicitNameGuard },
      block_reason: 'explicit_name_phrase_guard'
    }
  }];
}

if (parsed.type !== 'action' && parsed.type !== 'handoff' && selectedSlotGuard) {
  const baseContext = {
    ...(parsed.crm_context || {}),
    selected_date: selectedSlotGuard.date,
    selected_time: selectedSlotGuard.time,
    requested_slot_label: selectedSlotGuard.label,
    interesse: parsed.crm_context?.interesse || 'atendimento presencial'
  };

  if (!confirmedNameGuard) {
    return [{
      json: {
        type: 'response',
        message_blocks: [
          `Perfeito, consigo seguir com o horário ${selectedSlotGuard.label}.`,
          'Antes de registrar, me informa seu nome, por favor?'
        ],
        delay_seconds: 1,
        crm_context: { ...baseContext, customer_name: '' },
        block_reason: 'selected_slot_missing_name_guard'
      }
    }];
  }

  const firstName = formatSingleName(confirmedNameGuard.split(/\s+/)[0]);
  return [{
    json: {
      type: 'response',
      message_blocks: [
        `Perfeito, ${firstName}. Consigo seguir com o horário ${selectedSlotGuard.label}.`,
        'Para deixar o atendimento mais assertivo, me conta o motivo da visita ou a peça que você quer ver na loja?'
      ],
      delay_seconds: 1,
      crm_context: {
        ...baseContext,
        customer_name: confirmedNameGuard
      },
      block_reason: 'selected_slot_after_availability_guard'
    }
  }];
}

if (parsed.type !== 'action' && parsed.type !== 'handoff' && confirmedNameGuard && appointmentChoiceGuard) {
  const firstName = formatSingleName(confirmedNameGuard.split(/\s+/)[0]);
  return [{
    json: {
      type: 'action',
      action: 'check_availability',
      pre_message_blocks: [
        `Perfeito, ${firstName}. Vou verificar os horários disponíveis para atendimento presencial.`,
        'Aguarde um momento, por favor.'
      ],
      pre_delay_seconds: 1,
      arguments: { date: tomorrowSaoPauloDate(), period: 'qualquer' },
      crm_context: {
        ...(parsed.crm_context || {}),
        customer_name: confirmedNameGuard,
        interesse: parsed.crm_context?.interesse || 'atendimento presencial',
        visit_reason: parsed.crm_context?.visit_reason || 'atendimento presencial'
      },
      block_reason: 'confirmed_name_appointment_choice_guard'
    }
  }];
}

if (parsed.type !== 'action' && parsed.type !== 'handoff' && confirmedNameGuard && usefulVisitReasonGuard) {
  const firstName = formatSingleName(confirmedNameGuard.split(/\s+/)[0]);
  return [{
    json: {
      type: 'response',
      message_blocks: [
        `Perfeito, ${firstName}. Anotei essas informações para o atendimento.`,
        'Para registrar certinho, me passa seu nome completo e e-mail?',
        'Também confirma se este WhatsApp é o melhor número para contato?'
      ],
      delay_seconds: 1,
      crm_context: {
        ...(parsed.crm_context || {}),
        customer_name: confirmedNameGuard,
        visit_reason: userMessage,
        summary_for_human: userMessage
      },
      block_reason: 'visit_reason_collected_guard'
    }
  }];
}

if (parsed.type !== 'action' && parsed.type !== 'handoff' && !confirmedNameGuard && (availabilityListedStageGuard || askedVisitReasonStageGuard || offeredOptionsStageGuard) && !explicitNameGuard) {
  return [{
    json: {
      type: 'response',
      message_blocks: [
        'Antes de seguir, preciso confirmar seu nome.',
        'Me informa seu primeiro nome, por favor?'
      ],
      delay_seconds: 1,
      crm_context: { ...(parsed.crm_context || {}), customer_name: '' },
      block_reason: 'active_stage_missing_name_guard'
    }
  }];
}

if (parsed.type !== 'action' && parsed.type !== 'handoff' && confirmedNameGuard && appointmentIntentGuard && (responseTreatsInvalidNameGuard || !askedNameAgainGuard)) {
  const firstName = formatSingleName(confirmedNameGuard.split(/\s+/)[0]);
  return [{
    json: {
      type: 'action',
      action: 'check_availability',
      pre_message_blocks: [
        `Perfeito, ${firstName}. Vou verificar os horários disponíveis para atendimento presencial.`,
        'Aguarde um momento, por favor.'
      ],
      pre_delay_seconds: 1,
      arguments: { date: tomorrowSaoPauloDate(), period: 'qualquer' },
      crm_context: {
        ...(parsed.crm_context || {}),
        customer_name: confirmedNameGuard,
        interesse: parsed.crm_context?.interesse || 'atendimento presencial',
        visit_reason: parsed.crm_context?.visit_reason || 'atendimento presencial'
      },
      block_reason: 'confirmed_name_appointment_intent_guard'
    }
  }];
}

if (parsed.type !== 'action' && parsed.type !== 'handoff' && !confirmedNameGuard && (invalidParsedNameGuard || responseTreatsInvalidNameGuard || likelyNamePromptAnswerWithoutName)) {
  return [{
    json: {
      type: 'response',
      message_blocks: [
        'Ainda não consegui identificar seu nome.',
        'Me informa seu primeiro nome, por favor?'
      ],
      delay_seconds: 1,
      crm_context: { ...(parsed.crm_context || {}), customer_name: '' },
      block_reason: 'invalid_or_missing_name_repeat_prompt_guard'
    }
  }];
}

if (parsed.type !== 'action' && parsed.type !== 'handoff' && appointmentIntentGuard && !confirmedNameGuard) {
  return [{
    json: {
      type: 'response',
      message_blocks: [
        'Claro, posso te ajudar com o agendamento presencial.',
        'Antes de verificar os horários, me informa seu nome, por favor?'
      ],
      delay_seconds: 1,
      crm_context: { ...(parsed.crm_context || {}), customer_name: '' },
      block_reason: 'missing_valid_name_before_appointment_guard'
    }
  }];
}

if (parsed.type === 'action' && parsed.action === 'check_availability' && !confirmedNameGuard && isInvalidCustomerName(parsed.crm_context?.customer_name || '')) {
  return [{
    json: {
      type: 'response',
      message_blocks: [
        'Claro, posso verificar os horários para atendimento presencial.',
        'Antes disso, me informa seu nome, por favor?'
      ],
      delay_seconds: 1,
      crm_context: { ...(parsed.crm_context || {}), customer_name: '' },
      block_reason: 'missing_valid_name_before_check_availability_guard'
    }
  }];
}

if (parsed.type !== 'action' && parsed.type !== 'handoff' && confirmedNameGuard && appointmentIntentGuard && askedNameAgainGuard) {
  const firstName = formatSingleName(confirmedNameGuard.split(/\s+/)[0]);
  return [{
    json: {
      type: 'action',
      action: 'check_availability',
      pre_message_blocks: [
        `Perfeito, ${firstName}. Vou verificar os horários disponíveis para atendimento presencial.`,
        'Aguarde um momento, por favor.'
      ],
      pre_delay_seconds: 1,
      arguments: { date: tomorrowSaoPauloDate(), period: 'qualquer' },
      crm_context: {
        ...(parsed.crm_context || {}),
        customer_name: confirmedNameGuard,
        interesse: parsed.crm_context?.interesse || 'atendimento presencial',
        visit_reason: parsed.crm_context?.visit_reason || 'atendimento presencial'
      },
      block_reason: 'confirmed_name_from_history_appointment_guard'
    }
  }];
}

if (parsed.type === 'action' && parsed.action === 'check_availability') {
  parsed.arguments = parsed.arguments || parsed.action_args || {};
  if (!parsed.arguments.date) parsed.arguments.date = tomorrowSaoPauloDate();
}
""".strip()


def request_json(path: str, *, method: str = "GET", data: dict | None = None, timeout: int = 120) -> dict:
    if not API_KEY:
        raise SystemExit("N8N_API_KEY is required.")
    headers = {"Accept": "application/json", "X-N8N-API-KEY": API_KEY}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, method=method, headers=headers)
    try:
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")
        raise RuntimeError(f"n8n HTTP {err.code}: {detail}") from err
    return json.loads(raw) if raw else {}


def node_by_name(workflow: dict, name: str) -> dict:
    for node in workflow.get("nodes") or []:
        if node.get("name") == name:
            return node
    raise KeyError(f"Node not found: {name}")


def safe_settings(settings: dict | None) -> dict:
    allowed = {
        "timezone",
        "saveDataErrorExecution",
        "saveDataSuccessExecution",
        "saveManualExecutions",
        "saveExecutionProgress",
        "executionTimeout",
        "errorWorkflow",
        "executionOrder",
    }
    return {key: value for key, value in (settings or {}).items() if key in allowed}


def patch_code(js: str) -> str:
    old_guard_start = js.find("function getRawHistoryText()")
    new_guard_start = js.find("function normalizeNameForGuard(value)")
    if old_guard_start >= 0 and new_guard_start > old_guard_start:
        js = js[:old_guard_start] + js[new_guard_start:]
    elif old_guard_start >= 0:
        root_anchor_after_old = js.find("const rootCommand = /^\\s*\\//.test(msg);", old_guard_start)
        if root_anchor_after_old > old_guard_start:
            js = js[:old_guard_start] + js[root_anchor_after_old:]

    current_guard_start = js.find("function normalizeNameForGuard(value)")
    current_guard_end = js.find("const rootCommand = /^\\s*\\//.test(msg);", current_guard_start)
    if current_guard_start >= 0 and current_guard_end > current_guard_start:
        js = js[:current_guard_start] + js[current_guard_end:]

    anchor = "const rootCommand = /^\\s*\\//.test(msg);"
    if anchor not in js:
        raise RuntimeError("conversation guard anchor not found")
    js = js.replace(anchor, CONVERSATION_GUARD + "\n\n" + anchor, 1)

    js = js.replace(
        "'queria','ver','saber','obg','obrigado','obrigada','valeu','beleza','blz'",
        "'queria','ver','saber','obg','obrigado','obrigada','valeu','beleza','blz','tudo','sim','quero','gostaria','pode','agendar','agenda','atendimento','presencial','loja','marcar'",
    )
    js = js.replace(
        "const startsWithNonNamePhrase = /^(oi|olá|ola|bom\\s+dia|boa\\s+tarde|boa\\s+noite|onde|como|qual|quero|queria|gostaria|pode|preciso|tem|voces|vocês|endereco|endereço|localizacao|localização)\\b/i.test(msg);",
        "const startsWithNonNamePhrase = /^(oi|olá|ola|bom\\s+dia|boa\\s+tarde|boa\\s+noite|onde|como|qual|quero|queria|gostaria|pode|preciso|tem|voces|vocês|endereco|endereço|localizacao|localização|agendar|agenda|atendimento|presencial|loja|marcar|verificar)\\b/i.test(msg);",
    )
    js = js.replace(
        "const asksAddress = /(onde\\s+fica|endereco|endereço|localizacao|localização|maps|mapa|local|loja)/i.test(msg);",
        "const asksAddress = /(onde\\s+fica|qual(?:\\s+é|\\s+e)?\\s+o\\s+endere[cç]o|endere[cç]o|localiza[cç][aã]o|maps|mapa|como\\s+chegar|rota)/i.test(msg);",
    )
    js = js.replace(
        "visit_reason: visitReason\n  };",
        "visit_reason: visitReason,\n    customer_name: clean(args.customer_name || source.customer_name || source.nome || source.name),\n    customer_email: clean(args.customer_email || args.email || source.customer_email || source.email),\n    email: clean(args.email || source.email || source.customer_email)\n  };",
    )
    js = js.replace(
        "if (looksLikeOnlyTime && !hasExplicitDay) {\n  return responseAsk(\"Consigo seguir com esse horário, sim. Me confirma o dia, seu nome completo e o motivo da visita?\");\n}\n\n",
        "const timeOnlyCandidateGuard = looksLikeOnlyTime && !hasExplicitDay;\n\n",
    )
    js = js.replace(
        "if (parsed.type !== 'handoff' && !userAlreadyGaveName && !hasConfirmedNameInContext && (noRelevantContext || hasCommercialIntent || startsWithGreeting || msg.length <= 40) && !rootCommand) {",
        "if (parsed.type !== 'action' && parsed.type !== 'handoff' && !userAlreadyGaveName && !hasConfirmedNameInContext && !(typeof confirmedNameGuard !== 'undefined' && confirmedNameGuard) && (noRelevantContext || hasCommercialIntent || startsWithGreeting || msg.length <= 40) && !rootCommand) {",
    )
    js = js.replace(
        "if (parsed.type !== 'action' && parsed.type !== 'handoff' && !userAlreadyGaveName && !hasConfirmedNameInContext && (noRelevantContext || hasCommercialIntent || startsWithGreeting || msg.length <= 40) && !rootCommand) {",
        "if (parsed.type !== 'action' && parsed.type !== 'handoff' && !userAlreadyGaveName && !hasConfirmedNameInContext && !(typeof confirmedNameGuard !== 'undefined' && confirmedNameGuard) && !(typeof selectedSlotGuard !== 'undefined' && selectedSlotGuard) && !(typeof offeredOptionsStageGuard !== 'undefined' && offeredOptionsStageGuard) && !(typeof availabilityListedStageGuard !== 'undefined' && availabilityListedStageGuard) && !(typeof askedVisitReasonStageGuard !== 'undefined' && askedVisitReasonStageGuard) && (noRelevantContext || hasCommercialIntent || startsWithGreeting || msg.length <= 40) && !rootCommand) {",
    )
    js = js.replace("Prazer, ' + firstName + '.'", "Perfeito, ' + firstName + '.'")
    js = js.replace("Prazer, ", "Perfeito, ")
    js = js.replace("Qual você prefere?", "Qual opção você prefere?")
    js = js.replace("mostrar posso catálogo", "mostrar nosso catálogo")
    return js


def build_payload(workflow: dict) -> dict:
    nodes = json.loads(json.dumps(workflow.get("nodes") or []))
    webhook = node_by_name({"nodes": nodes}, "Webhook")
    path = webhook.get("parameters", {}).get("path")
    if path != WEBHOOK_PATH:
        raise RuntimeError(f"Webhook mismatch: expected {WEBHOOK_PATH}, got {path}")

    parser = node_by_name({"nodes": nodes}, "Code: Parse Agent Output")
    parser.setdefault("parameters", {})["jsCode"] = patch_code(parser.get("parameters", {}).get("jsCode", ""))

    payload = {
        "name": workflow["name"],
        "nodes": nodes,
        "connections": workflow.get("connections") or {},
        "settings": safe_settings(workflow.get("settings")),
    }
    if "staticData" in workflow:
        payload["staticData"] = workflow["staticData"]
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Patch Lara production conversation guardrails.")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    workflow = request_json(f"/api/v1/workflows/{WORKFLOW_ID}", timeout=120)
    before_path = ROOT / "backups" / f"n8n-lara-prod-before-conversation-guards-{timestamp}.json"
    payload_path = ROOT / "backups" / f"n8n-lara-prod-conversation-guards-payload-{timestamp}.json"
    before_path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = build_payload(workflow)
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = {
        "status": "dry_run",
        "apply": args.apply,
        "workflow_id": WORKFLOW_ID,
        "workflow_name": workflow.get("name"),
        "webhook_path": node_by_name(workflow, "Webhook").get("parameters", {}).get("path"),
        "backups": {
            "before": str(before_path.relative_to(ROOT)),
            "payload": str(payload_path.relative_to(ROOT)),
        },
    }
    if args.apply:
        updated = request_json(f"/api/v1/workflows/{WORKFLOW_ID}", method="PUT", data=payload, timeout=180)
        after_path = ROOT / "backups" / f"n8n-lara-prod-after-conversation-guards-{timestamp}.json"
        after_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["status"] = "applied"
        result["backups"]["after"] = str(after_path.relative_to(ROOT))

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
