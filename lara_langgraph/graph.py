from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph import START


STORE_ADDRESS = "Av. Brasil, 1500 - Centro, Balneário Camboriú - SC, 88330-901"
STORE_MAPS_URL = "https://maps.app.goo.gl/geMC3hHsQqGfSnnm6"


class LaraGraphState(TypedDict, total=False):
    session_id: str
    phone: str
    profile_name: str
    message: str
    normalized_message: str
    state: dict[str, Any]
    available_slots: list[dict[str, str]]
    qa_mode: bool
    intent: str
    conversation_stage: str
    lead_temperature: str
    reply_blocks: list[str]
    missing_fields: list[str]
    next_action: str
    tool_payload: dict[str, Any]
    crm_note: str
    safety: dict[str, Any]
    route: str


NON_NAME_MESSAGES = {
    "oi",
    "oii",
    "ola",
    "olá",
    "bom dia",
    "boa tarde",
    "boa noite",
    "ok",
    "okay",
    "sim",
    "s",
    "nao",
    "não",
    "confirmado",
    "confirma",
    "presencial",
}

APPOINTMENT_TERMS = (
    "agend",
    "agenda",
    "visita",
    "vizta",
    "presencial",
    "atendimento",
    "horario",
    "horário",
    "loja",
)

CATALOG_TERMS = ("catalogo", "catálogo", "modelo", "joia", "alianca", "aliança", "anel", "brinco")


def handle_turn(payload: dict[str, Any]) -> dict[str, Any]:
    """Run one Lara turn through the LangGraph state machine."""

    graph = _compiled_graph()
    initial: LaraGraphState = {
        "session_id": str(payload.get("session_id") or payload.get("phone") or ""),
        "phone": str(payload.get("phone") or ""),
        "profile_name": str(payload.get("profile_name") or ""),
        "message": str(payload.get("message") or ""),
        "available_slots": list(payload.get("available_slots") or []),
        "qa_mode": bool(payload.get("qa_mode", False)),
        "reply_blocks": [],
        "missing_fields": [],
        "next_action": "reply",
        "tool_payload": {},
        "lead_temperature": "morno",
        "safety": {"used_confirmed_facts_only": True, "needs_human": False},
    }
    if "state" in payload:
        initial["state"] = _initial_state(payload)

    config = {"configurable": {"thread_id": initial["session_id"]}}
    result = graph.invoke(initial, config)
    return _public_result(result)


@lru_cache(maxsize=1)
def _compiled_graph():
    workflow = StateGraph(LaraGraphState)
    workflow.add_node("normalize", _normalize)
    workflow.add_node("supervisor", _supervisor)
    workflow.add_node("identity", _identity)
    workflow.add_node("discovery", _discovery)
    workflow.add_node("appointment", _appointment)
    workflow.add_node("catalog_info", _catalog_info)
    workflow.add_node("closing", _closing)
    workflow.add_node("human_takeover", _human_takeover)

    workflow.add_edge(START, "normalize")
    workflow.add_edge("normalize", "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["route"],
        {
            "identity": "identity",
            "discovery": "discovery",
            "appointment": "appointment",
            "catalog_info": "catalog_info",
            "closing": "closing",
            "human_takeover": "human_takeover",
        },
    )
    for node in ("identity", "discovery", "appointment", "catalog_info", "closing", "human_takeover"):
        workflow.add_edge(node, END)
    return workflow.compile(checkpointer=InMemorySaver())


def _initial_state(payload: dict[str, Any]) -> dict[str, Any]:
    state = deepcopy(payload.get("state") or {})
    state.setdefault("conversation_stage", "inicio")
    state.setdefault("confirmed_name", None)
    state.setdefault("phone", payload.get("phone") or "")
    state.setdefault("last_intent", None)
    state.setdefault("last_bot_action", None)
    state.setdefault("last_offered_slots", [])
    state.setdefault("pending_booking", None)
    state.setdefault("collected_context", {})
    state.setdefault("human_takeover", False)
    return state


def _normalize(state: LaraGraphState) -> LaraGraphState:
    message = state.get("message", "")
    state["normalized_message"] = _normalize_text(message)
    if "state" not in state or not isinstance(state.get("state"), dict):
        state["state"] = _initial_state({"phone": state.get("phone", "")})
    state["state"]["phone"] = state.get("phone", "")
    return state


def _supervisor(state: LaraGraphState) -> LaraGraphState:
    current = state["state"].get("conversation_stage") or "inicio"
    text = state["normalized_message"]

    if state["state"].get("human_takeover") is True:
        state["route"] = "human_takeover"
        return state

    if current in {"agenda_slots", "agenda_contexto", "agenda_resumo_confirmacao", "agenda_criar"}:
        state["route"] = "appointment"
        return state

    if not state["state"].get("confirmed_name"):
        if _looks_like_name(state["message"], text):
            state["route"] = "identity"
            return state
        state["route"] = "identity"
        return state

    if _is_closing(text):
        state["route"] = "closing"
    elif _has_any(text, APPOINTMENT_TERMS):
        state["route"] = "appointment"
    elif _has_any(text, CATALOG_TERMS):
        state["route"] = "catalog_info"
    else:
        state["route"] = "discovery"
    return state


def _identity(state: LaraGraphState) -> LaraGraphState:
    text = state["normalized_message"]
    name = _extract_name(state["message"], text)

    if name:
        state["state"]["confirmed_name"] = name
        state["state"]["conversation_stage"] = "descoberta"
        state["intent"] = "discovery"
        state["conversation_stage"] = "descoberta"
        state["reply_blocks"] = [
            f"Perfeito, {name}.",
            "Me conta o que você está buscando hoje?",
            "Se quiser, posso te mostrar nosso catálogo de joias ou podemos agendar um atendimento presencial. Qual você prefere?",
        ]
        state["next_action"] = "reply"
        state["missing_fields"] = []
        return state

    greeting = _greeting_for(text)
    state["state"]["conversation_stage"] = "identificacao"
    state["intent"] = "identification"
    state["conversation_stage"] = "identificacao"
    state["reply_blocks"] = [
        f"Olá, {greeting}. Tudo bem?",
        "Aqui é a Lara, consultora virtual da ORIN Joias.",
        "Para que eu consiga te oferecer um atendimento mais preciso, você poderia me informar seu nome?",
    ]
    state["next_action"] = "reply"
    state["missing_fields"] = ["confirmed_name"]
    return state


def _discovery(state: LaraGraphState) -> LaraGraphState:
    text = state["normalized_message"]
    if _has_any(text, APPOINTMENT_TERMS):
        return _start_appointment(state)

    name = state["state"].get("confirmed_name")
    state["state"]["conversation_stage"] = "descoberta"
    state["intent"] = "discovery"
    state["conversation_stage"] = "descoberta"
    state["reply_blocks"] = [
        f"Entendi, {name}." if name else "Entendi.",
        "Me conta um pouco mais do que você procura, é uma joia para uma ocasião especial, personalização ou atendimento presencial?",
    ]
    state["next_action"] = "reply"
    return state


def _catalog_info(state: LaraGraphState) -> LaraGraphState:
    state["state"]["conversation_stage"] = "catalogo_info"
    state["intent"] = "catalog"
    state["conversation_stage"] = "catalogo_info"
    state["reply_blocks"] = [
        "Hoje ainda não tenho um catálogo online completo com link direto de cada produto.",
        "Posso entender o tipo de joia que você procura e te conduzir para um atendimento presencial ou para uma especialista verificar as opções com segurança.",
    ]
    state["next_action"] = "reply"
    return state


def _appointment(state: LaraGraphState) -> LaraGraphState:
    stage = state["state"].get("conversation_stage")
    if state.get("available_slots"):
        return _show_available_slots(state)

    if stage == "agenda_slots":
        return _handle_slot_selection(state)
    if stage == "agenda_contexto":
        return _collect_appointment_reason(state)
    if stage == "agenda_resumo_confirmacao":
        return _confirm_appointment(state)
    return _start_appointment(state)


def _show_available_slots(state: LaraGraphState) -> LaraGraphState:
    slots = list(state.get("available_slots") or [])
    state["intent"] = "appointment"
    state["conversation_stage"] = "agenda_slots"
    state["state"]["conversation_stage"] = "agenda_slots"
    state["state"]["last_offered_slots"] = slots
    state["reply_blocks"] = [
        "Tenho estes horários disponíveis:",
        *_format_slots(slots),
        "Qual desses horários funciona melhor para você?",
    ]
    state["next_action"] = "reply"
    state["missing_fields"] = ["selected_slot"]
    return state


def _start_appointment(state: LaraGraphState) -> LaraGraphState:
    slots = list(state.get("available_slots") or [])
    state["intent"] = "appointment"
    state["conversation_stage"] = "agenda_slots"
    state["state"]["conversation_stage"] = "agenda_slots"

    if slots:
        state["state"]["last_offered_slots"] = slots
        state["reply_blocks"] = [
            "Deixa eu verificar nossa agenda.",
            "Tenho estes horários disponíveis:",
            *_format_slots(slots),
            "Qual desses horários funciona melhor para você?",
        ]
        state["next_action"] = "reply"
        state["missing_fields"] = ["selected_slot"]
        return state

    state["reply_blocks"] = [
        "Deixa eu verificar nossa agenda.",
        "Aguarde um momento, por favor.",
    ]
    state["next_action"] = "check_availability"
    state["missing_fields"] = ["available_slots"]
    state["tool_payload"] = {
        "availability": {
            "date": _next_business_date(),
            "next_available": True,
        }
    }
    return state


def _handle_slot_selection(state: LaraGraphState) -> LaraGraphState:
    slot = _match_slot(state["normalized_message"], state["state"].get("last_offered_slots") or [])
    state["intent"] = "appointment"
    if not slot:
        state["conversation_stage"] = "agenda_slots"
        state["reply_blocks"] = ["Não consegui identificar qual horário você prefere. Pode me dizer o horário exato da lista?"]
        state["next_action"] = "reply"
        state["missing_fields"] = ["selected_slot"]
        return state

    state["state"]["pending_booking"] = slot
    state["state"]["conversation_stage"] = "agenda_contexto"
    state["conversation_stage"] = "agenda_contexto"
    state["reply_blocks"] = [
        "Perfeito.",
        "Para deixarmos o atendimento mais assertivo, qual é o motivo da sua visita e o que você gostaria de ver na loja?",
    ]
    state["next_action"] = "reply"
    state["missing_fields"] = ["appointment_reason"]
    return state


def _collect_appointment_reason(state: LaraGraphState) -> LaraGraphState:
    raw = state["message"].strip()
    context = state["state"].setdefault("collected_context", {})
    context["appointment_reason"] = raw
    context["interest"] = _infer_interest(state["normalized_message"])
    state["state"]["conversation_stage"] = "agenda_resumo_confirmacao"
    state["intent"] = "appointment"
    state["conversation_stage"] = "agenda_resumo_confirmacao"
    state["crm_note"] = _build_crm_note(state["state"])

    pending = state["state"].get("pending_booking") or {}
    name = state["state"].get("confirmed_name") or "cliente"
    state["reply_blocks"] = [
        _warm_acknowledgement(context["interest"]),
        f"Perfeito, {name}. Para confirmar: seu atendimento fica para {pending.get('label') or pending.get('date')} às {pending.get('time')}, e o assunto é {raw}.",
        "Confirma para mim se é isso mesmo?",
    ]
    state["next_action"] = "reply"
    state["missing_fields"] = ["customer_confirmation"]
    return state


def _confirm_appointment(state: LaraGraphState) -> LaraGraphState:
    text = state["normalized_message"]
    if not _is_confirmation(text):
        return _collect_appointment_reason(state)

    pending = state["state"].get("pending_booking") or {}
    context = state["state"].get("collected_context") or {}
    name = state["state"].get("confirmed_name")
    notes = _build_crm_note(state["state"])
    state["state"]["conversation_stage"] = "agenda_criar"
    state["intent"] = "appointment"
    state["conversation_stage"] = "agenda_criar"
    state["next_action"] = "create_appointment"
    if state.get("qa_mode"):
        state["next_action"] = "simulate_appointment"
    state["tool_payload"] = {
        "appointment": {
            "name": name,
            "phone": state["state"].get("phone") or state.get("phone"),
            "date": pending.get("date"),
            "time": pending.get("time"),
            "reason": context.get("appointment_reason"),
            "interest": context.get("interest"),
            "notes": notes,
        }
    }
    state["crm_note"] = notes
    state["reply_blocks"] = [
        "Prontinho, vou registrar seu agendamento agora.",
        f"Endereço da loja: {STORE_ADDRESS}.",
        f"Google Maps: {STORE_MAPS_URL}",
    ]
    state["missing_fields"] = []
    return state


def _closing(state: LaraGraphState) -> LaraGraphState:
    name = state["state"].get("confirmed_name")
    state["state"]["conversation_stage"] = "encerrado"
    state["intent"] = "closing"
    state["conversation_stage"] = "encerrado"
    state["reply_blocks"] = [f"Muito obrigada, {name}. Te aguardamos na ORIN Joias." if name else "Muito obrigada. Te aguardamos na ORIN Joias."]
    state["next_action"] = "reply"
    return state


def _human_takeover(state: LaraGraphState) -> LaraGraphState:
    state["intent"] = "human_takeover"
    state["conversation_stage"] = state["state"].get("conversation_stage", "handoff")
    state["reply_blocks"] = []
    state["next_action"] = "none"
    state["missing_fields"] = []
    state["safety"] = {"used_confirmed_facts_only": True, "needs_human": True}
    return state


def _public_result(state: LaraGraphState) -> dict[str, Any]:
    state_dict = state.get("state", {})
    next_action = state.get("next_action", "reply")
    qa_mode = bool(state.get("qa_mode", False))
    return {
        "reply_blocks": state.get("reply_blocks", []),
        "intent": state.get("intent", "discovery"),
        "conversation_stage": state.get("conversation_stage", state_dict.get("conversation_stage", "inicio")),
        "lead_temperature": state.get("lead_temperature", "morno"),
        "collected_context": state_dict.get("collected_context", {}),
        "missing_fields": state.get("missing_fields", []),
        "next_action": next_action,
        "tool_payload": state.get("tool_payload", {}),
        "crm_note": state.get("crm_note", ""),
        "state": state_dict,
        "safety": state.get("safety", {"used_confirmed_facts_only": True, "needs_human": False}),
        "side_effects": {
            "send_whatsapp": next_action == "reply" and bool(state.get("reply_blocks")) and not qa_mode,
            "create_appointment": next_action == "create_appointment" and not qa_mode,
            "update_crm": next_action in {"create_appointment", "check_availability"} and not qa_mode,
        },
    }


def _normalize_text(value: str) -> str:
    value = value.strip().lower()
    accents = str.maketrans("áàãâéêíóôõúç", "aaaaeeiooouc")
    return re.sub(r"\s+", " ", value.translate(accents))


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _looks_like_name(raw: str, normalized: str) -> bool:
    if normalized in NON_NAME_MESSAGES:
        return False
    if normalized.startswith("/"):
        return False
    if re.search(r"\d", normalized):
        return False
    if _has_any(normalized, APPOINTMENT_TERMS):
        return False
    words = [w for w in re.split(r"\s+", raw.strip()) if w]
    return 1 <= len(words) <= 4 and all(len(w) >= 2 for w in words)


def _extract_name(raw: str, normalized: str) -> str | None:
    patterns = [
        r"^(?:me chamo|meu nome e|meu nome é|sou|aqui e|aqui é)\s+(.+)$",
        r"^(.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, raw.strip(), flags=re.IGNORECASE)
        if not match:
            continue
        candidate = match.group(1).strip(" .,!?:;")
        if _looks_like_name(candidate, _normalize_text(candidate)):
            return " ".join(part.capitalize() for part in candidate.split())
    return None


def _greeting_for(text: str) -> str:
    if "bom dia" in text:
        return "bom dia"
    if "boa tarde" in text:
        return "boa tarde"
    if "boa noite" in text:
        return "boa noite"
    return "tudo bem"


def _format_slots(slots: list[dict[str, str]]) -> list[str]:
    formatted: list[str] = []
    for slot in slots:
        label = str(slot.get("label") or "").strip()
        time = str(slot.get("time") or "").strip()
        date = str(slot.get("date") or "").strip()
        if label and (not time or time in label):
            formatted.append(label)
        elif label:
            formatted.append(f"{label} - {time}")
        else:
            formatted.append(f"{date} - {time}".strip(" -"))
    return formatted


def _match_slot(text: str, slots: list[dict[str, str]]) -> dict[str, str] | None:
    hour_match = re.search(r"\b(\d{1,2})(?::?(\d{2}))?\b", text)
    if not hour_match:
        return None
    hour = int(hour_match.group(1))
    minute = hour_match.group(2) or "00"
    wanted = f"{hour:02d}:{minute}"
    for slot in slots:
        if slot.get("time") == wanted:
            return deepcopy(slot)
    return None


def _next_business_date() -> str:
    sao_paulo = timezone(timedelta(hours=-3))
    target = datetime.now(sao_paulo).date() + timedelta(days=1)
    if target.weekday() == 6:
        target += timedelta(days=1)
    return target.isoformat()


def _infer_interest(text: str) -> str:
    if "casamento" in text or "alianca" in text:
        return "alianças de casamento"
    if "noivado" in text or "anel" in text:
        return "anel de noivado"
    if "personaliz" in text or "gravacao" in text or "gravação" in text:
        return "personalização"
    return "atendimento em joias"


def _warm_acknowledgement(interest: str) -> str:
    if "casamento" in interest:
        return "Que especial, vai ser um prazer ajudar com uma joia para esse momento."
    if "noivado" in interest:
        return "Que momento bonito, vai ser uma honra ajudar nessa escolha."
    return "Perfeito, isso já ajuda bastante para preparar seu atendimento."


def _build_crm_note(state: dict[str, Any]) -> str:
    context = state.get("collected_context") or {}
    pending = state.get("pending_booking") or {}
    parts = [
        f"Cliente: {state.get('confirmed_name')}",
        f"Interesse: {context.get('interest')}",
        f"Motivo: {context.get('appointment_reason')}",
        f"Agenda: {pending.get('date')} {pending.get('time')}",
    ]
    return " | ".join(part for part in parts if not part.endswith("None"))


def _is_confirmation(text: str) -> bool:
    return text in {"sim", "confirmado", "confirma", "isso", "isso mesmo", "ok", "certo"} or "confirm" in text


def _is_closing(text: str) -> bool:
    return text in {"nao", "não", "so isso", "só isso", "obrigado", "obrigada"}
