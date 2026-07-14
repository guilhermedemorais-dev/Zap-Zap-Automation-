#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
from datetime import datetime


ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / "qa" / "lara_whatsapp_shadow_test.json"


CHECK_KEYS = [
    "greeting_asks_name_without_using_profile_name",
    "name_is_remembered_after_next_message",
    "appointment_intent_checks_availability_before_booking",
    "selected_time_without_reason_does_not_create_booking",
    "visit_reason_is_collected_before_confirmation",
    "address_is_correct_when_sent",
    "human_request_routes_to_specialist_or_handoff",
    "no_repeated_opening_loop",
    "no_wrong_customer_name",
    "no_obvious_hallucination",
]


def load() -> dict:
    if not TARGET.exists():
        raise SystemExit("Run scripts/lara_init_whatsapp_evidence.py first.")
    return json.loads(TARGET.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Record real WhatsApp shadow test evidence.")
    parser.add_argument("--tester", required=True)
    parser.add_argument("--test-number", required=True)
    parser.add_argument("--execution-id", action="append", default=[])
    parser.add_argument("--screenshot", action="append", default=[])
    parser.add_argument("--notes", default="")
    parser.add_argument("--approve", action="store_true", help="Mark status APPROVED and set all checklist items true.")
    parser.add_argument("--failure", action="append", default=[], help="Record a failure. Keeps status FAILED unless --approve is omitted.")
    args = parser.parse_args()

    data = load()
    data["tested_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    data["tester"] = args.tester
    data["test_number"] = args.test_number
    data["evidence"]["n8n_execution_ids"] = sorted(set([*data["evidence"].get("n8n_execution_ids", []), *args.execution_id]))
    data["evidence"]["screenshots"] = sorted(set([*data["evidence"].get("screenshots", []), *args.screenshot]))
    if args.notes:
        data["evidence"]["notes"] = args.notes
    if args.failure:
        data["failures"] = [*data.get("failures", []), *args.failure]
        data["status"] = "FAILED"
        data["approved_by_user"] = False
    if args.approve:
        if data.get("failures"):
            raise SystemExit("Cannot approve while failures are recorded.")
        if not data["evidence"].get("n8n_execution_ids") and not data["evidence"].get("screenshots"):
            raise SystemExit("Cannot approve without at least one execution id or screenshot.")
        data["status"] = "APPROVED"
        data["approved_by_user"] = True
        data["checklist"] = {key: True for key in CHECK_KEYS}

    TARGET.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": data["status"], "path": str(TARGET.relative_to(ROOT))}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
