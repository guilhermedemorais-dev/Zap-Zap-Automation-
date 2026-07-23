#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import time
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
JOURNEYS = ROOT / "qa" / "lara_qa_journeys.json"
OUT = ROOT / "qa" / "lara_journey_actual_outputs.json"
REPORT = ROOT / "qa" / "lara_journey_report.json"
EXEC_DIR = ROOT / "qa"

WORKFLOW_ID = os.environ.get("N8N_WORKFLOW_ID", "7kXu17NYpsN8Yc65")
WEBHOOK_PATH = os.environ.get("N8N_WEBHOOK_PATH", "whatsapp-inbound-v9-shadow")
BASE_URL = os.environ.get("N8N_BASE_URL", "https://n8n-zcac.srv1478933.hstgr.cloud").rstrip("/")
API_KEY = os.environ.get("N8N_API_KEY", "")

SIDE_EFFECT_NODES = {
    "Code: Enviar Pre-Blocos",
    "Code: Enviar Blocos",
    "Handoff: Msg ao Cliente",
    "ROOT: Enviar Resposta Admin",
    "ROOT: Enviar Resposta Livre",
    "Send Response",
    "CRM: Criar Appointment",
    "CRM: Registrar Mensagem",
    "CRM: Bot Reply",
    "CRM: Atualizar Lead",
    "CRM: Handoff Bot",
    "Handoff: Notificar Atendente",
    "CRM: Buscar Slots",
    "ROOT: Salvar Config Redis",
    "ROOT: Salvar Config Livre",
}


def request_json(url: str, *, method: str = "GET", data: dict | None = None, timeout: int = 120) -> dict:
    headers = {"Accept": "application/json"}
    if API_KEY:
        headers["X-N8N-API-KEY"] = API_KEY
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    return json.loads(raw) if raw else {}


def normalize(value: str) -> str:
    text = str(value or "").lower()
    replacements = str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc")
    return text.translate(replacements)


def includes_pattern(text: str, pattern: str) -> bool:
    return normalize(pattern) in normalize(text)


def regex_hits(text: str, pattern: str) -> bool:
    try:
        return re.search(pattern, text, flags=re.IGNORECASE) is not None
    except re.error:
        return includes_pattern(text, pattern)


def flatten_output(output: dict) -> str:
    return "\n".join(
        [
            str(output.get("type") or ""),
            str(output.get("action") or ""),
            *[str(block) for block in output.get("message_blocks") or []],
            json.dumps(output.get("action_args") or {}, ensure_ascii=False),
            json.dumps(output.get("crm_context") or {}, ensure_ascii=False),
        ]
    )


def payload_for(journey: dict, step: dict, fake_number: str, step_index: int, qa_history: str) -> dict:
    message = step.get("input", "")
    message_id = f"qa-journey-{journey['id'].lower()}-{step_index}-{int(time.time() * 1000)}"
    return {
        "EventType": "messages",
        "qa_mode": True,
        "scenario_id": f"{journey['id']}-STEP-{step_index}",
        "journey_id": journey["id"],
        "qa_history": qa_history,
        "fake_number": fake_number,
        "data": {
            "qa_mode": True,
            "scenario_id": f"{journey['id']}-STEP-{step_index}",
            "journey_id": journey["id"],
            "qa_history": qa_history,
            "fake_number": fake_number,
            "chatid": fake_number.replace("+", "") + "@s.whatsapp.net",
            "messageid": message_id,
            "text": message,
            "body": message,
            "pushName": "Cliente QA Jornada",
            "fromMe": False,
            "isGroup": False,
            "type": "text",
        },
    }


def latest_execution_id() -> str:
    url = f"{BASE_URL}/api/v1/executions?workflowId={WORKFLOW_ID}&limit=1&includeData=false"
    data = request_json(url, timeout=60)
    items = data.get("data") or []
    if not items:
        raise RuntimeError("No executions found.")
    return str(items[0]["id"])


def latest_execution_id_after(previous_id: str | None, timeout_seconds: float = 60.0) -> str:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        current_id = latest_execution_id()
        if previous_id is None or current_id != previous_id:
            return current_id
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for a new n8n execution after {previous_id}.")


def execution_output(execution_id: str) -> tuple[dict, dict]:
    url = f"{BASE_URL}/api/v1/executions/{execution_id}?includeData=true"
    execution = request_json(url, timeout=90)
    (EXEC_DIR / f"n8n_qa_execution_{execution_id}.json").write_text(
        json.dumps(execution, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    run_data = execution.get("data", {}).get("resultData", {}).get("runData", {})
    hits = sorted(SIDE_EFFECT_NODES & set(run_data.keys()))
    qa_runs = run_data.get("QA: Normalizar Output") or run_data.get("QA: Normalizar ROOT Output") or []
    if not qa_runs:
        raise RuntimeError(f"Execution {execution_id} did not reach QA output.")
    output = qa_runs[-1]["data"]["main"][0][0]["json"]
    meta = {
        "execution_id": execution_id,
        "forbidden_hits": hits,
        "nodes_executed": len(run_data),
        "root_qa": "QA: Normalizar ROOT Output" in run_data,
        "qa_output": "QA: Normalizar Output" in run_data,
    }
    return output, meta


def validate_step(journey: dict, step: dict, output: dict, meta: dict, global_forbidden: list[str]) -> list[str]:
    errors = []
    text = flatten_output(output)
    expected_type = step.get("expected_type")
    if expected_type and output.get("type") != expected_type:
        errors.append(f"expected type {expected_type}, got {output.get('type')}")
    expected_action = step.get("expected_action")
    if expected_action and output.get("action") != expected_action:
        errors.append(f"expected action {expected_action}, got {output.get('action')}")
    for pattern in step.get("required_patterns") or []:
        if not includes_pattern(text, pattern):
            errors.append(f'missing required pattern "{pattern}"')
    for pattern in [*global_forbidden, *(step.get("forbidden_patterns") or [])]:
        if regex_hits(text, pattern):
            errors.append(f'forbidden pattern hit "{pattern}"')
    if meta.get("forbidden_hits"):
        errors.append("side effect nodes reached: " + ", ".join(meta["forbidden_hits"]))
    blocks = output.get("message_blocks") or []
    if output.get("type") in {"response", "post_action_response", "handoff"} and not blocks:
        errors.append("response has no message_blocks")
    for index, block in enumerate(blocks, start=1):
        if len(str(block)) > 260:
            errors.append(f"block {index} too long ({len(str(block))} chars)")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="*", help="Journey IDs to run. Default: all.")
    parser.add_argument("--delay", type=float, default=14.0)
    args = parser.parse_args()

    if not API_KEY:
        raise SystemExit("Set N8N_API_KEY in the environment.")

    doc = json.loads(JOURNEYS.read_text(encoding="utf-8"))
    selected_ids = {value.upper() for value in (args.ids or [])}
    journeys = [
        journey
        for journey in doc.get("journeys", [])
        if not selected_ids or journey["id"].upper() in selected_ids
    ]

    actual = {"description": "Outputs reais multi-turn capturados do n8n QA Simulator", "journeys": {}}
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "workflow_id": WORKFLOW_ID,
        "webhook_path": WEBHOOK_PATH,
        "total_journeys": len(journeys),
        "passed": 0,
        "failed": 0,
        "results": [],
    }

    for journey_index, journey in enumerate(journeys, start=1):
        fake_number = f"+550000000{int(time.time() * 1000) % 1000000:06d}{journey_index:02d}"
        journey_outputs = []
        journey_errors = []
        for step_index, step in enumerate(journey.get("steps", []), start=1):
            previous_execution_id = latest_execution_id()
            qa_history = "\n".join(
                f"Cliente: {item['input']}\nLara: {' | '.join(item.get('output', {}).get('message_blocks') or [])}"
                for item in journey_outputs
            )
            request_json(
                f"{BASE_URL}/webhook/{WEBHOOK_PATH}",
                method="POST",
                data=payload_for(journey, step, fake_number, step_index, qa_history),
                timeout=120,
            )
            time.sleep(args.delay)
            execution_id = latest_execution_id_after(previous_execution_id)
            output, meta = execution_output(execution_id)
            errors = validate_step(journey, step, output, meta, doc.get("global_forbidden_patterns") or [])
            step_result = {
                "step": step_index,
                "input": step.get("input", ""),
                "execution_id": execution_id,
                "ok": not errors,
                "errors": errors,
                "output": {
                    key: value
                    for key, value in output.items()
                    if key in ["type", "action", "message_blocks", "action_args", "crm_context"]
                },
                "meta": meta,
            }
            journey_outputs.append(step_result)
            journey_errors.extend(f"step {step_index}: {error}" for error in errors)
            print(f"{journey['id']} step {step_index} -> execution {execution_id}")

        actual["journeys"][journey["id"]] = journey_outputs
        ok = not journey_errors
        report["passed" if ok else "failed"] += 1
        report["results"].append(
            {
                "id": journey["id"],
                "title": journey.get("title", ""),
                "fake_number": fake_number,
                "ok": ok,
                "errors": journey_errors,
                "executions": [step["execution_id"] for step in journey_outputs],
            }
        )

    OUT.write_text(json.dumps(actual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    print(f"Journeys: {report['passed']}/{report['total_journeys']} passed")
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
