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


FILTER_UAZAPI_JS = r"""
// Filter + normalize WhatsApp provider payloads into the UAZAPI-compatible shape
const input = $input.first().json || {};
const body = input.body || input;

function pick(...values) {
  for (const value of values) {
    if (value !== undefined && value !== null && String(value).trim() !== '') return value;
  }
  return '';
}

function normalizeJid(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  if (raw.includes('@')) return raw;
  const digits = raw.replace(/\D+/g, '');
  return digits ? `${digits}@s.whatsapp.net` : '';
}

function extractText(source) {
  const message = source.message || {};
  return pick(
    source.text,
    source.body,
    source.caption,
    source.content?.text,
    source.content?.body,
    message.conversation,
    message.extendedTextMessage?.text,
    message.imageMessage?.caption,
    message.videoMessage?.caption,
    message.documentMessage?.caption,
    message.buttonsResponseMessage?.selectedDisplayText,
    message.buttonsResponseMessage?.selectedButtonId,
    message.listResponseMessage?.title,
    message.listResponseMessage?.singleSelectReply?.selectedRowId,
    message.templateButtonReplyMessage?.selectedDisplayText,
    message.templateButtonReplyMessage?.selectedId
  );
}

const eventType = String(pick(body.EventType, body.event, body.type, body.eventType)).toLowerCase();
const allowedEvent =
  !eventType ||
  eventType === 'messages' ||
  eventType === 'message' ||
  eventType === 'messages.upsert' ||
  eventType === 'message.upsert' ||
  eventType === 'chat.message';
if (!allowedEvent) return [];

const msg = body.message?.key || body.message?.message || body.message?.text || body.message?.body || body.message?.chatid
  ? body.message
  : (body.data?.key || body.data?.message || body.data?.text || body.data?.body)
    ? body.data
    : body;

const key = msg.key || body.key || {};
const fromMe = msg.fromMe === true || key.fromMe === true || body.fromMe === true;
if (fromMe) return [];

const chatid = normalizeJid(pick(
  msg.chatid,
  msg.chatId,
  msg.remoteJid,
  key.remoteJid,
  body.chatid,
  body.chatId,
  body.remoteJid,
  body.from,
  body.sender
));

const isGroup = msg.isGroup === true || body.isGroup === true || chatid.endsWith('@g.us');
if (isGroup) return [];

const text = String(extractText(msg) || extractText(body) || '').trim();
const rawType = String(pick(msg.messageType, msg.type, msg.mediaType, body.messageType, body.type, 'text')).toLowerCase();
const hasMedia = ['image', 'audio', 'video', 'document', 'sticker', 'ptt', 'imagemessage', 'audiomessage', 'videomessage', 'documentmessage'].includes(rawType);
if (!text && !hasMedia) return [];

const messageId = String(pick(
  msg.messageid,
  msg.messageId,
  msg.id,
  key.id,
  body.messageid,
  body.messageId,
  body.id,
  `msg-${Date.now()}`
));

const pushName = String(pick(
  msg.pushName,
  msg.senderName,
  msg.notifyName,
  body.pushName,
  body.senderName,
  body.chat?.name,
  'Cliente'
));

const normalizedMessageType = pick(
  msg.messageType,
  body.messageType,
  hasMedia ? rawType.replace(/message$/, '') + 'Message' : 'conversation'
);

return [{
  json: {
    ...input,
    qa_mode: !!(input.qa_mode || body.qa_mode || msg.qa_mode),
    body: {
      ...body,
      qa_mode: !!(input.qa_mode || body.qa_mode || msg.qa_mode),
      data: {
        ...msg,
        qa_mode: !!(input.qa_mode || body.qa_mode || msg.qa_mode),
        fake_number: pick(input.fake_number, body.fake_number, msg.fake_number),
        key: {
          ...key,
          id: messageId,
          remoteJid: chatid,
          fromMe: false
        },
        pushName,
        message: {
          ...(msg.message || {}),
          conversation: text
        },
        messageType: normalizedMessageType,
        text,
        body: text,
        chatid,
        messageid: messageId,
        id: messageId
      }
    }
  }
}];
""".strip() + "\n"


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


def build_payload(workflow: dict) -> dict:
    nodes = json.loads(json.dumps(workflow.get("nodes") or []))
    webhook = node_by_name({"nodes": nodes}, "Webhook")
    webhook_path = webhook.get("parameters", {}).get("path")
    if webhook_path != SHADOW_WEBHOOK_PATH:
        raise RuntimeError(f"Shadow webhook mismatch: expected {SHADOW_WEBHOOK_PATH}, got {webhook_path}")

    filter_node = node_by_name({"nodes": nodes}, "Filter UAZAPI")
    filter_node.setdefault("parameters", {})["jsCode"] = FILTER_UAZAPI_JS

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
    parser = argparse.ArgumentParser(description="Patch Lara V9 shadow input normalizer.")
    parser.add_argument("--apply", action="store_true", help="Update remote shadow workflow.")
    args = parser.parse_args()

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    workflow = request_json(f"/api/v1/workflows/{SHADOW_WORKFLOW_ID}", timeout=120)
    before_path = ROOT / "backups" / f"n8n-lara-v9-shadow-before-input-contract-{timestamp}.json"
    payload_path = ROOT / "backups" / f"n8n-lara-v9-shadow-input-contract-payload-{timestamp}.json"
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
        after_path = ROOT / "backups" / f"n8n-lara-v9-shadow-after-input-contract-{timestamp}.json"
        after_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["status"] = "applied"
        result["backups"]["after"] = str(after_path.relative_to(ROOT))

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
