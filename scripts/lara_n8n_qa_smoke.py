#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "qa" / "lara_qa_scenarios.json"
OUT = ROOT / "qa" / "lara_actual_outputs.json"
EXEC_DIR = ROOT / "qa"

WORKFLOW_ID = os.environ.get("N8N_WORKFLOW_ID", "7SucjAi8zU69sQuT")
WEBHOOK_PATH = os.environ.get("N8N_WEBHOOK_PATH", "whatsapp-inbound")
BASE_URL = os.environ.get("N8N_BASE_URL", "https://n8n-zcac.srv1478933.hstgr.cloud").rstrip("/")
API_KEY = os.environ.get("N8N_API_KEY", "")


def request_json(url, *, method="GET", data=None, timeout=120):
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


def scenario_payload(scenario, index):
    fake = f"+550000000{index:03d}"
    message = scenario.get("input", "")
    return {
        "EventType": "messages",
        "qa_mode": True,
        "scenario_id": scenario["id"],
        "fake_number": fake,
        "data": {
            "qa_mode": True,
            "scenario_id": scenario["id"],
            "fake_number": fake,
            "chatid": fake.replace("+", "") + "@s.whatsapp.net",
            "messageid": f"qa-20260630-{scenario['id'].lower()}-{int(time.time())}",
            "text": message,
            "body": message,
            "pushName": "Cliente QA",
            "fromMe": False,
            "isGroup": False,
            "type": "text",
        },
    }


def latest_execution_id():
    if not API_KEY:
        raise SystemExit("N8N_API_KEY is required to fetch execution output.")
    url = f"{BASE_URL}/api/v1/executions?workflowId={WORKFLOW_ID}&limit=1&includeData=false"
    data = request_json(url, timeout=60)
    items = data.get("data") or []
    if not items:
        raise RuntimeError("No executions found.")
    return str(items[0]["id"])


def latest_execution_id_after(previous_id, timeout_seconds=60.0):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        current_id = latest_execution_id()
        if previous_id is None or current_id != previous_id:
            return current_id
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for a new n8n execution after {previous_id}.")


def execution_output(execution_id):
    url = f"{BASE_URL}/api/v1/executions/{execution_id}?includeData=true"
    execution = request_json(url, timeout=90)
    (EXEC_DIR / f"n8n_qa_execution_{execution_id}.json").write_text(
        json.dumps(execution, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    run_data = execution.get("data", {}).get("resultData", {}).get("runData", {})
    side_effect_nodes = {
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
    }
    hits = sorted(side_effect_nodes & set(run_data.keys()))
    if hits:
        raise RuntimeError(f"Side effect nodes reached in QA: {', '.join(hits)}")
    qa_runs = run_data.get("QA: Normalizar Output") or run_data.get("QA: Normalizar ROOT Output") or []
    if not qa_runs:
        raise RuntimeError(f"Execution {execution_id} did not reach QA output.")
    return qa_runs[-1]["data"]["main"][0][0]["json"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="*", help="Scenario IDs to run. Default: QA-01 only.")
    parser.add_argument("--all", action="store_true", help="Run all scenarios. Costs LLM calls.")
    parser.add_argument("--delay", type=float, default=14.0, help="Seconds to wait after webhook start.")
    args = parser.parse_args()

    if not API_KEY:
        raise SystemExit("Set N8N_API_KEY in the environment.")

    doc = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    scenarios = doc["scenarios"]
    selected_ids = {s.upper() for s in (args.ids or [])}
    if args.all:
        selected = scenarios
    elif selected_ids:
        selected = [s for s in scenarios if s["id"].upper() in selected_ids]
    else:
        selected = [s for s in scenarios if s["id"] == "QA-01"]

    outputs = {}
    for idx, scenario in enumerate(selected, start=1):
        payload = scenario_payload(scenario, idx)
        previous_execution_id = latest_execution_id()
        request_json(f"{BASE_URL}/webhook/{WEBHOOK_PATH}", method="POST", data=payload, timeout=120)
        time.sleep(args.delay)
        execution_id = latest_execution_id_after(previous_execution_id)
        out = execution_output(execution_id)
        outputs[scenario["id"]] = {
            key: value
            for key, value in out.items()
            if key in ["type", "action", "message_blocks", "action_args", "crm_context"]
        }
        outputs[scenario["id"]]["execution_id"] = execution_id
        print(f"{scenario['id']} -> execution {execution_id}")

    OUT.write_text(
        json.dumps({"description": "Outputs reais capturados do n8n QA Simulator", "outputs": outputs}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
