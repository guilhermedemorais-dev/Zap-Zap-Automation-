#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / "qa" / "lara_v9_langgraph_bridge_report.json"

BASE_URL = os.environ.get("N8N_BASE_URL", "https://n8n-zcac.srv1478933.hstgr.cloud/api/v1").rstrip("/")
API_KEY = os.environ.get("N8N_API_KEY", "")
V9_WORKFLOW_ID = os.environ.get("LARA_V9_WORKFLOW_ID", "7kXu17NYpsN8Yc65")
V7_WORKFLOW_ID = os.environ.get("LARA_V7_WORKFLOW_ID", "7SucjAi8zU69sQuT")


def request_json(path: str) -> dict:
    if not API_KEY:
        raise RuntimeError("N8N_API_KEY is required.")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={"X-N8N-API-KEY": API_KEY, "Accept": "application/json"},
    )
    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    return json.loads(raw) if raw else {}


def targets(workflow: dict, source: str) -> list[str]:
    output: list[str] = []
    cfg = workflow.get("connections", {}).get(source, {})
    for branch in cfg.get("main", []) or []:
        output.extend(str(conn.get("node")) for conn in branch if conn.get("node"))
    return output


def has_connection(workflow: dict, source: str, target: str) -> bool:
    return target in targets(workflow, source)


def node_names(workflow: dict) -> set[str]:
    return {str(node.get("name")) for node in workflow.get("nodes", [])}


def node_by_name(workflow: dict, name: str) -> dict:
    for node in workflow.get("nodes", []):
        if node.get("name") == name:
            return node
    return {}


def main() -> int:
    v9 = request_json(f"/workflows/{V9_WORKFLOW_ID}")
    v7 = request_json(f"/workflows/{V7_WORKFLOW_ID}")
    names = node_names(v9)
    slots_node = node_by_name(v9, "CRM: Buscar Slots")
    create_node = node_by_name(v9, "CRM: Criar Appointment")
    slot_query_names = {
        param.get("name")
        for param in (slots_node.get("parameters", {}).get("queryParameters", {}).get("parameters") or [])
    }
    create_body = str(create_node.get("parameters", {}).get("jsonBody", ""))

    checks = [
        {
            "name": "v9_active",
            "ok": v9.get("active") is True,
            "details": {"id": V9_WORKFLOW_ID, "name": v9.get("name"), "active": v9.get("active")},
        },
        {
            "name": "v7_inactive_during_v9_test",
            "ok": v7.get("active") is False,
            "details": {"id": V7_WORKFLOW_ID, "name": v7.get("name"), "active": v7.get("active")},
        },
        {
            "name": "langgraph_nodes_exist",
            "ok": {"Lara LangGraph Turn", "Code: Slots Para LangGraph", "IF: CRM Retornou Slots", "Lara LangGraph Slots Turn"} <= names,
            "details": {"missing": sorted({"Lara LangGraph Turn", "Code: Slots Para LangGraph", "IF: CRM Retornou Slots", "Lara LangGraph Slots Turn"} - names)},
        },
        {
            "name": "root_calls_langgraph_instead_of_ai_agent",
            "ok": has_connection(v9, "ROOT: Injetar Regras", "Lara LangGraph Turn") and not has_connection(v9, "ROOT: Injetar Regras", "AI Agent"),
            "details": {"targets": targets(v9, "ROOT: Injetar Regras")},
        },
        {
            "name": "langgraph_output_preserves_existing_parser_contract",
            "ok": has_connection(v9, "Lara LangGraph Turn", "Code: Parse Agent Output"),
            "details": {"targets": targets(v9, "Lara LangGraph Turn")},
        },
        {
            "name": "crm_slots_return_to_langgraph_memory",
            "ok": (
                has_connection(v9, "CRM: Buscar Slots", "Code: Slots Para LangGraph")
                and has_connection(v9, "Code: Slots Para LangGraph", "IF: CRM Retornou Slots")
                and has_connection(v9, "IF: CRM Retornou Slots", "Lara LangGraph Slots Turn")
                and has_connection(v9, "Lara LangGraph Slots Turn", "Code: Parse Final Output")
            ),
            "details": {
                "crm_targets": targets(v9, "CRM: Buscar Slots"),
                "slot_formatter_targets": targets(v9, "Code: Slots Para LangGraph"),
                "slot_if_targets": targets(v9, "IF: CRM Retornou Slots"),
                "slot_langgraph_targets": targets(v9, "Lara LangGraph Slots Turn"),
            },
        },
        {
            "name": "crm_slots_query_contract",
            "ok": {"date", "next_available"} <= slot_query_names,
            "details": {
                "url": slots_node.get("parameters", {}).get("url"),
                "query_names": sorted(slot_query_names),
            },
        },
        {
            "name": "booking_confirmation_bypasses_free_llm",
            "ok": (
                has_connection(v9, "CRM: Criar Appointment", "Code: Formatar Tool Result")
                and has_connection(v9, "Code: Formatar Tool Result", "Code: Parse Final Output")
                and not has_connection(v9, "Code: Formatar Tool Result", "LLM: Resposta Final Agendamento")
            ),
            "details": {
                "crm_create_targets": targets(v9, "CRM: Criar Appointment"),
                "tool_result_targets": targets(v9, "Code: Formatar Tool Result"),
            },
        },
        {
            "name": "crm_create_payload_contract",
            "ok": all(token in create_body for token in ("customer_name", "customer_email", "visit_reason", "ai_context")),
            "details": {
                "url": create_node.get("parameters", {}).get("url"),
                "has_customer_name": "customer_name" in create_body,
                "has_customer_email": "customer_email" in create_body,
                "has_visit_reason": "visit_reason" in create_body,
                "has_ai_context": "ai_context" in create_body,
            },
        },
    ]

    status = "PASS" if all(check["ok"] for check in checks) else "FAIL"
    report = {"status": status, "checks": checks}
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
