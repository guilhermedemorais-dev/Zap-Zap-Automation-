#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("N8N_BASE_URL", "https://n8n-zcac.srv1478933.hstgr.cloud").rstrip("/")
API_KEY = os.environ.get("N8N_API_KEY", "")
WORKFLOW_ID = "7SucjAi8zU69sQuT"


def request_json(path, *, method="GET", data=None, timeout=120):
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
        body = err.read().decode("utf-8", "replace")
        raise RuntimeError(f"n8n HTTP {err.code}: {body}") from err
    return json.loads(raw) if raw else {}


def publish(workflow_path, before_path, after_path):
    current = request_json(f"/api/v1/workflows/{WORKFLOW_ID}", timeout=90)
    before_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    draft = json.loads(workflow_path.read_text(encoding="utf-8"))
    allowed_settings = {
        "timezone",
        "saveDataErrorExecution",
        "saveDataSuccessExecution",
        "saveManualExecutions",
        "saveExecutionProgress",
        "executionTimeout",
        "errorWorkflow",
        "executionOrder",
    }
    settings = {
        key: value
        for key, value in (draft.get("settings") or {}).items()
        if key in allowed_settings
    }

    payload = {
        "name": draft["name"],
        "nodes": draft["nodes"],
        "connections": draft.get("connections", {}),
        "settings": settings,
    }
    if "staticData" in draft:
        payload["staticData"] = draft["staticData"]

    updated = request_json(f"/api/v1/workflows/{WORKFLOW_ID}", method="PUT", data=payload, timeout=180)
    after = request_json(f"/api/v1/workflows/{WORKFLOW_ID}", timeout=90)
    after_path.write_text(json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "updated_name": updated.get("name") or after.get("name"),
        "workflow_id": after.get("id"),
        "active": after.get("active"),
        "node_count": len(after.get("nodes") or []),
        "connection_count": len(after.get("connections") or {}),
        "before": str(before_path.relative_to(ROOT)),
        "after": str(after_path.relative_to(ROOT)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", default="backups/n8n-ORION-WF-Bot-v7-with-address-name-loop-fix-draft-20260701.json")
    parser.add_argument("--before", default="backups/n8n-ORION-WF-Bot-v7-before-address-name-loop-fix-20260701.json")
    parser.add_argument("--after", default="backups/n8n-ORION-WF-Bot-v7-after-address-name-loop-fix-20260701.json")
    args = parser.parse_args()

    result = publish(
        ROOT / args.workflow,
        ROOT / args.before,
        ROOT / args.after,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
