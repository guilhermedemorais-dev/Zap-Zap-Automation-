#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import pathlib
import time
import unicodedata
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("N8N_BASE_URL", "https://n8n-zcac.srv1478933.hstgr.cloud").rstrip("/")
API_KEY = os.environ.get("N8N_API_KEY", "")
WEBHOOK_PATH = os.environ.get("N8N_WEBHOOK_PATH", "whatsapp-inbound-v9-shadow")
WORKFLOW_ID = os.environ.get("N8N_WORKFLOW_ID", "7kXu17NYpsN8Yc65")
PAYLOADS = ROOT / "qa" / "lara_input_contract_payloads.json"
REPORT = ROOT / "qa" / "lara_input_contract_report.json"


FORBIDDEN_NODES = [
    "Code: Enviar",
    "CRM: Criar",
    "CRM: Atualizar",
    "CRM: Registrar",
    "Agenda:",
    "ROOT: Save",
    "ROOT: Persist",
]


def request_json(url_or_path: str, *, method: str = "GET", data: dict | None = None, timeout: int = 120) -> dict:
    headers = {"Accept": "application/json"}
    if url_or_path.startswith("/api/"):
        if not API_KEY:
            raise SystemExit("N8N_API_KEY is required.")
        headers["X-N8N-API-KEY"] = API_KEY
        url = f"{BASE_URL}{url_or_path}"
    else:
        url = url_or_path
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {err.code}: {detail}") from err
    return json.loads(raw) if raw else {}


def list_recent_executions() -> list[dict]:
    data = request_json(f"/api/v1/executions?workflowId={WORKFLOW_ID}&limit=12", timeout=120)
    return data.get("data") or data.get("results") or []


def get_execution(execution_id: str) -> dict:
    return request_json(f"/api/v1/executions/{execution_id}?includeData=true", timeout=120)


def find_new_execution(before_ids: set[str]) -> dict | None:
    for execution in list_recent_executions():
        execution_id = str(execution.get("id"))
        if execution_id not in before_ids:
            return get_execution(execution_id)
    return None


def qa_output(execution: dict) -> dict | None:
    run_data = execution.get("data", {}).get("resultData", {}).get("runData", {})
    for node_name in ["QA: Normalizar Output", "QA: Normalizar ROOT Output"]:
        node_runs = run_data.get(node_name) or []
        for run in node_runs:
            for branch in run.get("data", {}).get("main", []) or []:
                for item in branch or []:
                    payload = item.get("json", {})
                    if payload:
                        return payload
    return None


def output_text(payload: dict | None) -> str:
    if not payload:
        return ""
    chunks: list[str] = []
    if isinstance(payload.get("message_blocks"), list):
        chunks.extend(str(block) for block in payload["message_blocks"])
    if payload.get("response"):
        chunks.append(str(payload["response"]))
    if payload.get("text"):
        chunks.append(str(payload["text"]))
    return "\n".join(chunks)


def side_effect_failures(execution: dict) -> list[str]:
    failures: list[str] = []
    run_data = execution.get("data", {}).get("resultData", {}).get("runData", {})
    for node_name in run_data:
        if any(token in node_name for token in FORBIDDEN_NODES):
            failures.append(node_name)
    return failures


def comparable(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def set_nested(payload: dict, path: list[str], value: str) -> None:
    current = payload
    for key in path[:-1]:
        if not isinstance(current.get(key), dict):
            current[key] = {}
        current = current[key]
    current[path[-1]] = value


def set_nested_if_parent_exists(payload: dict, path: list[str], value: str) -> None:
    current = payload
    for key in path[:-1]:
        if not isinstance(current.get(key), dict):
            return
        current = current[key]
    current[path[-1]] = value


def payload_with_unique_id(payload: dict, case_id: str) -> dict:
    cloned = copy.deepcopy(payload)
    unique = f"{case_id.lower()}-{int(time.time() * 1000)}"
    set_nested(cloned, ["id"], unique)
    set_nested(cloned, ["messageid"], unique)
    set_nested_if_parent_exists(cloned, ["message", "id"], unique)
    set_nested_if_parent_exists(cloned, ["message", "messageid"], unique)
    set_nested_if_parent_exists(cloned, ["message", "key", "id"], unique)
    set_nested_if_parent_exists(cloned, ["data", "id"], unique)
    set_nested_if_parent_exists(cloned, ["data", "messageid"], unique)
    set_nested_if_parent_exists(cloned, ["data", "key", "id"], unique)
    return cloned


def main() -> None:
    parser = argparse.ArgumentParser(description="Run remote input-contract smoke tests against Lara shadow webhook.")
    parser.add_argument("--delay", type=float, default=14.0)
    args = parser.parse_args()

    cases = json.loads(PAYLOADS.read_text(encoding="utf-8"))
    before_ids = {str(item.get("id")) for item in list_recent_executions()}
    results: list[dict] = []

    for case in cases:
        url = f"{BASE_URL}/webhook/{WEBHOOK_PATH}"
        request_json(url, method="POST", data=payload_with_unique_id(case["payload"], case["id"]), timeout=60)
        time.sleep(args.delay)
        execution = find_new_execution(before_ids)
        if not execution:
            results.append({"id": case["id"], "ok": False, "errors": ["No new execution found"]})
            continue
        execution_id = str(execution.get("id"))
        before_ids.add(execution_id)
        output = qa_output(execution)
        text = output_text(output)
        lower = comparable(text)
        errors = []
        if not output:
            errors.append("No QA normalized output found")
        elif output.get("type") == "qa_error":
            errors.append(f"QA error: {output.get('error')}")
        for expected in case.get("expected_contains") or []:
            if comparable(expected) not in lower:
                errors.append(f"Missing expected text: {expected}")
        forbidden = side_effect_failures(execution)
        if forbidden:
            errors.append(f"Forbidden side effects: {', '.join(forbidden)}")
        results.append({
            "id": case["id"],
            "ok": not errors,
            "execution_id": execution_id,
            "errors": errors,
            "output_excerpt": text[:800],
        })

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "workflow_id": WORKFLOW_ID,
        "webhook_path": WEBHOOK_PATH,
        "passed": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "results": results,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
