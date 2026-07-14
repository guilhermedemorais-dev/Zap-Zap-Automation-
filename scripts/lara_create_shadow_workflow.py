#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("N8N_BASE_URL", "https://n8n-zcac.srv1478933.hstgr.cloud").rstrip("/")
API_KEY = os.environ.get("N8N_API_KEY", "")
SOURCE_WORKFLOW_ID = os.environ.get("LARA_SOURCE_WORKFLOW_ID", "7SucjAi8zU69sQuT")
DEFAULT_SHADOW_NAME = "LARA V9 Shadow SDR"


def request_json(path: str, *, method: str = "GET", data: dict | None = None, timeout: int = 120) -> dict:
    if not API_KEY:
        raise SystemExit("N8N_API_KEY is required.")

    headers = {
        "Accept": "application/json",
        "X-N8N-API-KEY": API_KEY,
    }
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


def list_workflows() -> list[dict]:
    workflows: list[dict] = []
    cursor = None
    while True:
        query = {"limit": "100"}
        if cursor:
            query["cursor"] = cursor
        path = "/api/v1/workflows?" + urllib.parse.urlencode(query)
        page = request_json(path, timeout=90)
        workflows.extend(page.get("data") or [])
        cursor = page.get("nextCursor")
        if not cursor:
            return workflows


def build_shadow_payload(source: dict, shadow_name: str) -> dict:
    payload = {
        "name": shadow_name,
        "nodes": source.get("nodes") or [],
        "connections": source.get("connections") or {},
        "settings": safe_settings(source.get("settings")),
    }
    if "staticData" in source:
        payload["staticData"] = source["staticData"]
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an inactive Lara V9 Shadow workflow from the current production workflow.")
    parser.add_argument("--shadow-name", default=DEFAULT_SHADOW_NAME)
    parser.add_argument("--apply", action="store_true", help="Create the workflow in n8n. Default is dry-run only.")
    args = parser.parse_args()

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    source = request_json(f"/api/v1/workflows/{SOURCE_WORKFLOW_ID}", timeout=120)
    backup_path = ROOT / "backups" / f"n8n-lara-source-before-shadow-{timestamp}.json"
    payload_path = ROOT / "backups" / f"n8n-lara-v9-shadow-payload-{timestamp}.json"
    backup_path.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    existing = [workflow for workflow in list_workflows() if workflow.get("name") == args.shadow_name]
    if existing:
        print(json.dumps({
            "status": "exists",
            "shadow_name": args.shadow_name,
            "existing_ids": [workflow.get("id") for workflow in existing],
            "source_backup": str(backup_path.relative_to(ROOT)),
        }, ensure_ascii=False, indent=2))
        return

    payload = build_shadow_payload(source, args.shadow_name)
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.apply:
        print(json.dumps({
            "status": "dry_run",
            "shadow_name": args.shadow_name,
            "source_workflow_id": SOURCE_WORKFLOW_ID,
            "source_backup": str(backup_path.relative_to(ROOT)),
            "payload": str(payload_path.relative_to(ROOT)),
            "node_count": len(payload["nodes"]),
            "connection_count": len(payload["connections"]),
            "active": False,
        }, ensure_ascii=False, indent=2))
        return

    created = request_json("/api/v1/workflows", method="POST", data=payload, timeout=180)
    print(json.dumps({
        "status": "created",
        "shadow_name": created.get("name"),
        "shadow_id": created.get("id"),
        "active": created.get("active"),
        "source_backup": str(backup_path.relative_to(ROOT)),
        "payload": str(payload_path.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
