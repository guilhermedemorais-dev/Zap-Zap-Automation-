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
PROD_WORKFLOW_ID = os.environ.get("LARA_PROD_WORKFLOW_ID", "7SucjAi8zU69sQuT")
SHADOW_WORKFLOW_ID = os.environ.get("LARA_SHADOW_WORKFLOW_ID", "7kXu17NYpsN8Yc65")
PROD_WEBHOOK_PATH = os.environ.get("LARA_PROD_WEBHOOK_PATH", "whatsapp-inbound")
SHADOW_WEBHOOK_PATH = os.environ.get("LARA_SHADOW_WEBHOOK_PATH", "whatsapp-inbound-v9-shadow")
READINESS_REPORT = ROOT / "qa" / "lara_production_readiness_report.json"
CONFIRM_TEXT = "PROMOVER LARA V9 PARA PRODUCAO"


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


def node_by_name(workflow: dict, name: str) -> dict:
    for node in workflow.get("nodes") or []:
        if node.get("name") == name:
            return node
    raise KeyError(f"Node not found: {name}")


def assert_readiness_ready() -> dict:
    if not READINESS_REPORT.exists():
        raise RuntimeError(f"Readiness report not found: {READINESS_REPORT}")
    report = json.loads(READINESS_REPORT.read_text(encoding="utf-8"))
    if report.get("status") != "READY_FOR_PRODUCTION_APPROVAL":
        blockers = ", ".join(report.get("blockers") or [])
        raise RuntimeError(f"Readiness is not approved. Current blockers: {blockers or 'unknown'}")
    return report


def build_promotion_payload(prod: dict, shadow: dict) -> dict:
    nodes = json.loads(json.dumps(shadow.get("nodes") or []))
    webhook = node_by_name({"nodes": nodes}, "Webhook")
    webhook.setdefault("parameters", {})["path"] = PROD_WEBHOOK_PATH

    payload = {
        "name": prod["name"],
        "nodes": nodes,
        "connections": shadow.get("connections") or {},
        "settings": safe_settings(shadow.get("settings")),
    }
    if "staticData" in shadow:
        payload["staticData"] = shadow["staticData"]
    return payload


def workflow_summary(workflow: dict) -> dict:
    webhook = node_by_name(workflow, "Webhook")
    return {
        "id": workflow.get("id"),
        "name": workflow.get("name"),
        "active": workflow.get("active"),
        "webhook_path": webhook.get("parameters", {}).get("path"),
        "node_count": len(workflow.get("nodes") or []),
        "connection_count": len(workflow.get("connections") or {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare or apply Lara V9 Shadow promotion into the production workflow."
    )
    parser.add_argument("--apply", action="store_true", help="Actually update the production workflow.")
    parser.add_argument("--confirm", default="", help=f"Required with --apply: {CONFIRM_TEXT}")
    parser.add_argument(
        "--allow-blocked-dry-run",
        action="store_true",
        help="Allow dry-run while readiness is still blocked. Never works with --apply.",
    )
    args = parser.parse_args()

    if args.apply and args.allow_blocked_dry_run:
        raise SystemExit("--allow-blocked-dry-run cannot be used with --apply.")
    if args.apply and args.confirm != CONFIRM_TEXT:
        raise SystemExit(f"--apply requires --confirm '{CONFIRM_TEXT}'")

    readiness = None
    try:
        readiness = assert_readiness_ready()
    except RuntimeError as err:
        if args.apply or not args.allow_blocked_dry_run:
            raise
        readiness = {"status": "BLOCKED_DRY_RUN_ALLOWED", "warning": str(err)}

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    prod = request_json(f"/api/v1/workflows/{PROD_WORKFLOW_ID}", timeout=120)
    shadow = request_json(f"/api/v1/workflows/{SHADOW_WORKFLOW_ID}", timeout=120)

    prod_webhook = node_by_name(prod, "Webhook").get("parameters", {}).get("path")
    shadow_webhook = node_by_name(shadow, "Webhook").get("parameters", {}).get("path")
    if prod_webhook != PROD_WEBHOOK_PATH:
        raise RuntimeError(f"Production webhook mismatch: expected {PROD_WEBHOOK_PATH}, got {prod_webhook}")
    if shadow_webhook != SHADOW_WEBHOOK_PATH:
        raise RuntimeError(f"Shadow webhook mismatch: expected {SHADOW_WEBHOOK_PATH}, got {shadow_webhook}")

    prod_backup = ROOT / "backups" / f"n8n-lara-prod-before-v9-promotion-{timestamp}.json"
    shadow_backup = ROOT / "backups" / f"n8n-lara-shadow-source-for-v9-promotion-{timestamp}.json"
    payload_path = ROOT / "backups" / f"n8n-lara-prod-v9-promotion-payload-{timestamp}.json"
    prod_backup.write_text(json.dumps(prod, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shadow_backup.write_text(json.dumps(shadow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = build_promotion_payload(prod, shadow)
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = {
        "status": "dry_run",
        "apply": args.apply,
        "readiness_status": readiness.get("status"),
        "production_before": workflow_summary(prod),
        "shadow_source": workflow_summary(shadow),
        "production_payload": {
            "name": payload["name"],
            "webhook_path": node_by_name({"nodes": payload["nodes"]}, "Webhook").get("parameters", {}).get("path"),
            "node_count": len(payload["nodes"]),
            "connection_count": len(payload["connections"]),
        },
        "backups": {
            "production_before": str(prod_backup.relative_to(ROOT)),
            "shadow_source": str(shadow_backup.relative_to(ROOT)),
            "payload": str(payload_path.relative_to(ROOT)),
        },
    }

    if args.apply:
        updated = request_json(f"/api/v1/workflows/{PROD_WORKFLOW_ID}", method="PUT", data=payload, timeout=180)
        result["status"] = "applied"
        result["production_after"] = workflow_summary(updated)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
