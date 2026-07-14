from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


KNOWN_COMMANDS = {
    "/help",
    "/status",
    "/parametro",
    "/persona",
    "/tom",
    "/objetivo",
    "/regra",
    "/escrita",
    "/corrigir",
    "/exemplo",
    "/link",
    "/newprompt",
    "/clear",
    "/reset",
    "/exit",
    "/log",
    "/tutorial",
    "/assumir",
    "/devolver",
    "/bot",
}


def parse_root_command(message: str) -> dict[str, Any]:
    """Parse ROOT commands deterministically, without LLM interpretation."""

    text = (message or "").strip()
    if not text.startswith("/"):
        return {"is_command": False, "command": None, "args": "", "known": False}

    command, _, args = text.partition(" ")
    command = command.lower()
    known = command in KNOWN_COMMANDS
    return {
        "is_command": True,
        "command": command,
        "args": args.strip(),
        "known": known,
        "error": None if known else "unknown_command",
    }


def apply_root_command(message: str, root_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Apply safe ROOT Console state transitions.

    This function only returns deterministic state patches and admin reply blocks.
    Persistence, authorization and audit-log writes stay in n8n/CRM.
    """

    state = deepcopy(root_state or {})
    if state.get("pending_action") == "reset" and message.strip() == "CONFIRMAR RESET":
        return {
            "type": "root_reset_confirmed",
            "parsed": {"is_command": False, "command": "CONFIRMAR RESET", "args": "", "known": True},
            "state_patch": {"pending_action": None, "config_reset": True},
            "reply_blocks": ["Reset confirmado. A configuração da Lara foi restaurada para a base padrão."],
        }

    if state.get("pending_action") == "reset" and message.strip().lower() == "cancelar":
        return {
            "type": "root_reset_cancelled",
            "parsed": {"is_command": False, "command": "cancelar", "args": "", "known": True},
            "state_patch": {"pending_action": None},
            "reply_blocks": ["Reset cancelado. Nenhuma configuração foi alterada."],
        }

    parsed = parse_root_command(message)
    if not parsed["is_command"]:
        return {
            "type": "root_free_text",
            "parsed": parsed,
            "state_patch": {},
            "reply_blocks": [
                "Pode ser mais específico?",
                "Use /help para ver os comandos disponíveis.",
            ],
        }

    if not parsed["known"]:
        return {
            "type": "root_error",
            "parsed": parsed,
            "state_patch": {},
            "reply_blocks": [
                "Comando não reconhecido.",
                "Use /help para ver os comandos disponíveis.",
            ],
        }

    command = parsed["command"]
    args = parsed["args"]

    if command == "/reset":
        return {
            "type": "root_reset_pending",
            "parsed": parsed,
            "state_patch": {"pending_action": "reset"},
            "reply_blocks": [
                "Atenção: /reset apaga toda a configuração atual da Lara.",
                "Para confirmar, responda exatamente: CONFIRMAR RESET",
                "Para cancelar, responda: cancelar",
            ],
        }

    if command == "/assumir":
        target = _extract_phone(args)
        return {
            "type": "root_takeover_started",
            "parsed": parsed,
            "state_patch": {
                "target_phone": target,
                "conversation_patch": {"human_takeover": True},
            },
            "reply_blocks": ["Atendimento assumido. A Lara está pausada para este cliente."],
        }

    if command in {"/devolver", "/bot"}:
        target = _extract_phone(args)
        return {
            "type": "root_takeover_finished",
            "parsed": parsed,
            "state_patch": {
                "target_phone": target,
                "conversation_patch": {"human_takeover": False},
            },
            "reply_blocks": ["Atendimento devolvido para a Lara."],
        }

    if command in {"/persona", "/tom", "/objetivo", "/regra", "/escrita", "/corrigir", "/exemplo", "/link", "/newprompt"}:
        if not args:
            return {
                "type": "root_validation_error",
                "parsed": parsed,
                "state_patch": {},
                "reply_blocks": ["Informe o texto da alteração depois do comando."],
            }
        return {
            "type": "root_draft_created",
            "parsed": parsed,
            "state_patch": {
                "draft": {
                    "command": command,
                    "args": args,
                    "status": "pending_confirmation",
                }
            },
            "reply_blocks": [
                "Rascunho criado.",
                "Revise a alteração antes de confirmar.",
            ],
        }

    return {
        "type": "root_readonly",
        "parsed": parsed,
        "state_patch": {},
        "reply_blocks": ["Comando recebido."],
    }


def _extract_phone(value: str) -> str | None:
    digits = re.sub(r"\D+", "", value or "")
    if not digits:
        return None
    if digits.startswith("55"):
        return f"+{digits}"
    if len(digits) in {10, 11}:
        return f"+55{digits}"
    return f"+{digits}"
