#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
QA_REPORT = ROOT / "qa" / "lara_qa_report.json"
JOURNEY_REPORT = ROOT / "qa" / "lara_journey_report.json"
INPUT_CONTRACT_REPORT = ROOT / "qa" / "lara_input_contract_report.json"
READY_REPORT = ROOT / "qa" / "lara_production_readiness_report.json"
DEFAULT_WHATSAPP_EVIDENCE = ROOT / "qa" / "lara_whatsapp_shadow_test.json"

BASE_URL = os.environ.get("N8N_BASE_URL", "https://n8n-zcac.srv1478933.hstgr.cloud").rstrip("/")
API_KEY = os.environ.get("N8N_API_KEY", "")
PROD_WORKFLOW_ID = os.environ.get("LARA_PROD_WORKFLOW_ID", "7SucjAi8zU69sQuT")
SHADOW_WORKFLOW_ID = os.environ.get("LARA_SHADOW_WORKFLOW_ID", "7kXu17NYpsN8Yc65")
PROD_WEBHOOK_PATH = os.environ.get("LARA_PROD_WEBHOOK_PATH", "whatsapp-inbound")
SHADOW_WEBHOOK_PATH = os.environ.get("LARA_SHADOW_WEBHOOK_PATH", "whatsapp-inbound-v9-shadow")

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


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def request_json(path: str, timeout: int = 90) -> dict:
    if not API_KEY:
        raise RuntimeError("N8N_API_KEY is required.")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={"X-N8N-API-KEY": API_KEY, "Accept": "application/json"},
    )
    raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    return json.loads(raw) if raw else {}


def workflow_status(workflow_id: str) -> dict:
    workflow = request_json(f"/api/v1/workflows/{workflow_id}")
    webhook = next((node for node in workflow.get("nodes", []) if node.get("name") == "Webhook"), None)
    return {
        "id": workflow_id,
        "name": workflow.get("name"),
        "active": workflow.get("active"),
        "webhook_path": (webhook or {}).get("parameters", {}).get("path"),
    }


def check_execution_side_effects(execution_id: str) -> dict:
    path = ROOT / "qa" / f"n8n_qa_execution_{execution_id}.json"
    if not path.exists():
        return {"execution": execution_id, "ok": False, "error": "execution file missing", "forbidden_hits": []}
    data = load_json(path)
    run = data.get("data", {}).get("resultData", {}).get("runData", {})
    hits = sorted(SIDE_EFFECT_NODES & set(run.keys()))
    reached_qa = "QA: Normalizar Output" in run or "QA: Normalizar ROOT Output" in run
    return {
        "execution": execution_id,
        "ok": not hits and reached_qa,
        "forbidden_hits": hits,
        "reached_qa": reached_qa,
        "nodes_executed": len(run),
    }


def collect_single_turn_executions() -> list[str]:
    outputs = load_json(ROOT / "qa" / "lara_actual_outputs.json").get("outputs") or {}
    return [
        str(item.get("execution_id"))
        for item in outputs.values()
        if isinstance(item, dict) and item.get("execution_id")
    ]


def collect_journey_executions(report: dict) -> list[str]:
    executions: list[str] = []
    for result in report.get("results", []):
        executions.extend(str(value) for value in result.get("executions", []))
    return executions


def validate_whatsapp_evidence(path: pathlib.Path) -> dict:
    if not path.exists():
        return {"ok": False, "error": "evidence file missing", "path": str(path.relative_to(ROOT))}
    evidence = load_json(path)
    required_url = f"{BASE_URL}/webhook/{SHADOW_WEBHOOK_PATH}"
    checklist = evidence.get("checklist") or {}
    missing_checks = [key for key, value in checklist.items() if value is not True]
    failures = evidence.get("failures") or []
    execution_ids = evidence.get("evidence", {}).get("n8n_execution_ids") or []
    screenshots = evidence.get("evidence", {}).get("screenshots") or []
    ok = (
        evidence.get("status") == "APPROVED"
        and evidence.get("approved_by_user") is True
        and evidence.get("shadow_webhook_url") == required_url
        and not missing_checks
        and not failures
        and bool(execution_ids or screenshots)
    )
    return {
        "ok": ok,
        "path": str(path.relative_to(ROOT)),
        "status": evidence.get("status"),
        "approved_by_user": evidence.get("approved_by_user"),
        "shadow_webhook_url": evidence.get("shadow_webhook_url"),
        "required_url": required_url,
        "missing_checks": missing_checks,
        "failures": failures,
        "evidence_count": {
            "n8n_execution_ids": len(execution_ids),
            "screenshots": len(screenshots),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--whatsapp-evidence",
        default=str(DEFAULT_WHATSAPP_EVIDENCE),
        help="JSON evidence file for the real WhatsApp shadow test.",
    )
    args = parser.parse_args()

    checks: list[dict] = []
    blockers: list[str] = []

    qa_report = load_json(QA_REPORT)
    journey_report = load_json(JOURNEY_REPORT)
    input_contract_report = load_json(INPUT_CONTRACT_REPORT)

    prod = workflow_status(PROD_WORKFLOW_ID)
    shadow = workflow_status(SHADOW_WORKFLOW_ID)
    checks.append({"name": "prod_webhook_unchanged", "ok": prod["webhook_path"] == PROD_WEBHOOK_PATH and prod["active"] is True, "details": prod})
    checks.append({"name": "shadow_webhook_active", "ok": shadow["webhook_path"] == SHADOW_WEBHOOK_PATH and shadow["active"] is True, "details": shadow})

    checks.append({
        "name": "single_turn_actual_outputs",
        "ok": qa_report.get("mode") == "actual_outputs" and qa_report.get("passed") == 22 and qa_report.get("failed") == 0 and qa_report.get("jsonl_ok") is True,
        "details": {
            "mode": qa_report.get("mode"),
            "passed": qa_report.get("passed"),
            "failed": qa_report.get("failed"),
            "jsonl_ok": qa_report.get("jsonl_ok"),
            "generated_at": qa_report.get("generated_at"),
        },
    })
    checks.append({
        "name": "multi_turn_journeys",
        "ok": journey_report.get("passed") == 3 and journey_report.get("failed") == 0,
        "details": {
            "passed": journey_report.get("passed"),
            "failed": journey_report.get("failed"),
            "generated_at": journey_report.get("generated_at"),
        },
    })
    checks.append({
        "name": "input_contract_payloads",
        "ok": (
            input_contract_report.get("workflow_id") == SHADOW_WORKFLOW_ID
            and input_contract_report.get("webhook_path") == SHADOW_WEBHOOK_PATH
            and input_contract_report.get("passed") == 4
            and input_contract_report.get("failed") == 0
        ),
        "details": {
            "workflow_id": input_contract_report.get("workflow_id"),
            "webhook_path": input_contract_report.get("webhook_path"),
            "passed": input_contract_report.get("passed"),
            "failed": input_contract_report.get("failed"),
            "generated_at": input_contract_report.get("generated_at"),
            "execution_ids": [
                item.get("execution_id")
                for item in input_contract_report.get("results", [])
                if item.get("execution_id")
            ],
        },
    })

    side_effect_checks = [
        *(check_execution_side_effects(execution_id) for execution_id in collect_single_turn_executions()),
        *(check_execution_side_effects(execution_id) for execution_id in collect_journey_executions(journey_report)),
    ]
    failed_side_effect = [item for item in side_effect_checks if not item.get("ok")]
    checks.append({
        "name": "qa_side_effects_blocked",
        "ok": not failed_side_effect,
        "details": {
            "checked_executions": len(side_effect_checks),
            "failures": failed_side_effect,
        },
    })

    whatsapp_evidence = validate_whatsapp_evidence(pathlib.Path(args.whatsapp_evidence))
    checks.append({
        "name": "real_whatsapp_shadow_test",
        "ok": whatsapp_evidence["ok"],
        "details": whatsapp_evidence,
    })

    for check in checks:
        if not check["ok"]:
            blockers.append(check["name"])

    report = {
        "status": "READY_FOR_PRODUCTION_APPROVAL" if not blockers else "BLOCKED",
        "blockers": blockers,
        "checks": checks,
    }
    READY_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not blockers else 1


if __name__ == "__main__":
    sys.exit(main())
