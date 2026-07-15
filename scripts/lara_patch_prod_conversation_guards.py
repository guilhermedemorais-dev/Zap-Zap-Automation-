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
    'lara', 'orin'
  ]);
  if (!first || invalid.has(normalized)) return true;
  return !/^[A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]{2,30}$/.test(first);
}

function findConfirmedCustomerNameFromRuntime() {
  const rawParts = [contextText || ''];
  try { rawParts.push(String($('Get chat_history').first().json.history || '')); } catch(e) {}
  try {
    const raw = $('Get chat_history1').first().json.propertyName;
    rawParts.push(Array.isArray(raw) ? raw.join('\n') : String(raw || ''));
  } catch(e) {}

  const parsedName = normalizeNameForGuard(parsed.crm_context?.customer_name || '');
  if (parsedName && !isInvalidCustomerName(parsedName)) return parsedName;

  const source = rawParts.filter(Boolean).join('\n');
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

function tomorrowSaoPauloDate() {
  const now = new Date();
  const spNow = new Date(now.toLocaleString('en-US', { timeZone: 'America/Sao_Paulo' }));
  spNow.setDate(spNow.getDate() + 1);
  const yyyy = spNow.getFullYear();
  const mm = String(spNow.getMonth() + 1).padStart(2, '0');
  const dd = String(spNow.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

const appointmentIntentGuard = /(atendimento\s+presencial|agendar|agenda|visita|horário|horario|marcar|atendimento)/i.test(msg);
const askedNameAgainGuard = /(?:informar|dizer|me passa|me informe|qual (?:é|e))[^.!?\n]{0,80}\b(?:seu\s+)?nome\b|nome\?/i.test(responseText);
const confirmedNameGuard = findConfirmedCustomerNameFromRuntime();
const invalidParsedNameGuard = isInvalidCustomerName(parsed.crm_context?.customer_name || '') ? normalizeNameForGuard(parsed.crm_context?.customer_name || '') : '';
const responseTreatsInvalidNameGuard = /\b(?:Perfeito|Prazer|Olá|Ola),\s*(Tudo|Tdo|Sim|Ok|Okay|Quero|Gostaria|Meu|Filho)\b/i.test(responseText);
const likelyNamePromptAnswerWithoutName = (
  /\b(tudo|tdo|sim|ok|okay|quero|gostaria|pode|claro|meu filho|já disse|ja disse)\b/i.test(msg)
  && !confirmedNameGuard
  && !/^\s*(meu nome é|me chamo|sou o|sou a)\s+[A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]/i.test(userMessage)
);

if (confirmedNameGuard) {
  parsed.crm_context = { ...(parsed.crm_context || {}), customer_name: confirmedNameGuard };
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
        "'queria','ver','saber','obg','obrigado','obrigada','valeu','beleza','blz','tudo','sim','quero','gostaria','pode'",
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
        "if (parsed.type !== 'handoff' && !userAlreadyGaveName && !hasConfirmedNameInContext && (noRelevantContext || hasCommercialIntent || startsWithGreeting || msg.length <= 40) && !rootCommand) {",
        "if (parsed.type !== 'action' && parsed.type !== 'handoff' && !userAlreadyGaveName && !hasConfirmedNameInContext && (noRelevantContext || hasCommercialIntent || startsWithGreeting || msg.length <= 40) && !rootCommand) {",
    )
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
