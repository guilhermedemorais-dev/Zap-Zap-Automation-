#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "qa" / "lara_whatsapp_shadow_test.example.json"
TARGET = ROOT / "qa" / "lara_whatsapp_shadow_test.json"


def main() -> None:
    if TARGET.exists():
        print(json.dumps({"status": "exists", "path": str(TARGET.relative_to(ROOT))}, ensure_ascii=False, indent=2))
        return
    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    TARGET.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "created", "path": str(TARGET.relative_to(ROOT))}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
