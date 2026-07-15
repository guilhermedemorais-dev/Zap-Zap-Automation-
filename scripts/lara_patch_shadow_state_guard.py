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
SHADOW_WORKFLOW_ID = os.environ.get("LARA_SHADOW_WORKFLOW_ID", "7kXu17NYpsN8Yc65")
SHADOW_WEBHOOK_PATH = os.environ.get("LARA_SHADOW_WEBHOOK_PATH", "whatsapp-inbound-v9-shadow")


STATE_GUARD_SNIPPET = r"""
function getRawHistoryText() {
  const parts = [];
  try { parts.push(String($('Get chat_history').first().json.history || '')); } catch(e) {}
  try {
    const raw = $('Get chat_history1').first().json.propertyName;
    if (Array.isArray(raw)) parts.push(raw.join('\n'));
    else parts.push(String(raw || ''));
  } catch(e) {}
  try { parts.push(String($('Webhook').item.json.body?.qa_history || $('Webhook').item.json.qa_history || '')); } catch(e) {}
  return parts.filter(Boolean).join('\n');
}

function extractConfirmedCustomerName(text) {
  const source = String(text || '');
  const patterns = [
    /customer_name["']?\s*[:=]\s*["']([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+(?:[ \t]+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+){0,3})["']/,
    /\b(?:Client name|Nome do cliente|Cliente|Nome)\s*[:\-]\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+(?:[ \t]+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+){0,3})/i,
    /\bPrazer,\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+(?:[ \t]+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+){0,3})\b/
  ];
  const blacklist = new Set(['Cliente', 'Orin', 'Lara', 'Boa', 'Bom', 'Olá', 'Ola']);
  for (const pattern of patterns) {
    const match = source.match(pattern);
    if (!match) continue;
    const candidate = clean(match[1]).replace(/[.!?]+$/g, '');
    const first = candidate.split(/\s+/)[0];
    if (first && !blacklist.has(first)) return candidate;
  }
  return '';
}

const rawHistoryText = getRawHistoryText();
const confirmedCustomerNameFromHistory = clean(parsed.crm_context?.customer_name || extractConfirmedCustomerName(contextText + '\n' + rawHistoryText));
const confirmedCustomerFirstName = confirmedCustomerNameFromHistory ? formatSingleName(confirmedCustomerNameFromHistory.split(/\s+/)[0]) : '';
const askedNameAgain = /(?:informar|dizer|me passa|me informe|qual (?:é|e))[^.!?\n]{0,80}\b(?:seu\s+)?nome\b|nome\?/i.test(responseText);
const appointmentIntent = /(atendimento\s+presencial|agendar|agenda|visita|horário|horario|marcar|atendimento)/i.test(msg);
const uncertaintyText = /(não entendi|nao entendi|não consegui entender|nao consegui entender|pode repetir|explique melhor|não ficou claro|nao ficou claro)/i.test(responseText);

if (confirmedCustomerNameFromHistory) {
  parsed.crm_context = { ...(parsed.crm_context || {}), customer_name: confirmedCustomerNameFromHistory };
}

if (parsed.type !== 'action' && parsed.type !== 'handoff' && confirmedCustomerNameFromHistory && appointmentIntent && askedNameAgain) {
  return [{
    json: {
      type: 'action',
      action: 'check_availability',
      pre_message_blocks: [
        `Perfeito, ${confirmedCustomerFirstName}. Vou verificar os horários disponíveis para atendimento presencial.`,
        'Aguarde um momento, por favor.'
      ],
      pre_delay_seconds: 1,
      arguments: { period: 'qualquer' },
      crm_context: {
        ...(parsed.crm_context || {}),
        customer_name: confirmedCustomerNameFromHistory,
        interesse: parsed.crm_context?.interesse || 'atendimento presencial',
        visit_reason: parsed.crm_context?.visit_reason || 'atendimento presencial'
      },
      block_reason: 'confirmed_name_from_history_appointment_guard'
    }
  }];
}

if (parsed.type !== 'action' && parsed.type !== 'handoff' && confirmedCustomerNameFromHistory && askedNameAgain) {
  return [{
    json: {
      type: 'response',
      message_blocks: [
        `Perfeito, ${confirmedCustomerFirstName}.`,
        'Me confirma só o que você prefere agora: ver o catálogo, tirar uma dúvida sobre joias ou agendar um atendimento presencial?'
      ],
      delay_seconds: 1,
      crm_context: { ...(parsed.crm_context || {}), customer_name: confirmedCustomerNameFromHistory },
      block_reason: 'do_not_ask_name_twice_guard'
    }
  }];
}

if (parsed.type !== 'action' && parsed.type !== 'handoff' && uncertaintyText) {
  return [{
    json: {
      type: 'response',
      message_blocks: [
        'Perdão, não entendi muito bem.',
        'Você quer ver nosso catálogo, tirar uma dúvida sobre joias ou agendar um atendimento presencial?'
      ],
      delay_seconds: 1,
      crm_context: parsed.crm_context || {},
      block_reason: 'low_confidence_fallback_guard'
    }
  }];
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


def patch_parser_code(js: str) -> str:
    if "confirmed_name_from_history_appointment_guard" in js:
        return js

    anchor = "const explicitNamePhrase = userMessage.trim().match"
    if anchor not in js:
        raise RuntimeError("Parser insertion anchor not found.")

    return js.replace(anchor, STATE_GUARD_SNIPPET + "\n\n" + anchor, 1)


def build_payload(workflow: dict) -> dict:
    nodes = json.loads(json.dumps(workflow.get("nodes") or []))
    webhook = node_by_name({"nodes": nodes}, "Webhook")
    webhook_path = webhook.get("parameters", {}).get("path")
    if webhook_path != SHADOW_WEBHOOK_PATH:
        raise RuntimeError(f"Shadow webhook mismatch: expected {SHADOW_WEBHOOK_PATH}, got {webhook_path}")

    parser = node_by_name({"nodes": nodes}, "Code: Parse Agent Output")
    parser.setdefault("parameters", {})["jsCode"] = patch_parser_code(parser.get("parameters", {}).get("jsCode", ""))

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
    parser = argparse.ArgumentParser(description="Patch Lara V9 shadow state guard.")
    parser.add_argument("--apply", action="store_true", help="Update remote shadow workflow.")
    args = parser.parse_args()

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    workflow = request_json(f"/api/v1/workflows/{SHADOW_WORKFLOW_ID}", timeout=120)
    before_path = ROOT / "backups" / f"n8n-lara-v9-shadow-before-state-guard-{timestamp}.json"
    payload_path = ROOT / "backups" / f"n8n-lara-v9-shadow-state-guard-payload-{timestamp}.json"
    before_path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = build_payload(workflow)
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = {
        "status": "dry_run",
        "apply": args.apply,
        "workflow_id": SHADOW_WORKFLOW_ID,
        "workflow_name": workflow.get("name"),
        "webhook_path": node_by_name(workflow, "Webhook").get("parameters", {}).get("path"),
        "backups": {
            "before": str(before_path.relative_to(ROOT)),
            "payload": str(payload_path.relative_to(ROOT)),
        },
    }
    if args.apply:
        updated = request_json(f"/api/v1/workflows/{SHADOW_WORKFLOW_ID}", method="PUT", data=payload, timeout=180)
        after_path = ROOT / "backups" / f"n8n-lara-v9-shadow-after-state-guard-{timestamp}.json"
        after_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["status"] = "applied"
        result["backups"]["after"] = str(after_path.relative_to(ROOT))

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
