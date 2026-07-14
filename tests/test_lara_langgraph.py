import unittest
from itertools import count

from lara_langgraph.graph import handle_turn
from lara_langgraph.root_console import apply_root_command, parse_root_command


_session_counter = count(1)


def run_turn(message, state=None, **extra):
    payload = {
        "session_id": f"wa:+554799999{next(_session_counter):04d}",
        "phone": "+5547999990000",
        "profile_name": "Teste orin",
        "message": message,
    }
    if state is not None:
        payload["state"] = state
    payload.update(extra)
    return handle_turn(payload)


class LaraLangGraphTest(unittest.TestCase):
    def test_short_greeting_asks_name_without_using_profile_name(self):
        result = run_turn("Boa noite")

        self.assertEqual(result["intent"], "identification")
        self.assertEqual(result["conversation_stage"], "identificacao")
        self.assertEqual(result["next_action"], "reply")
        text = "\n".join(result["reply_blocks"])
        self.assertIn("Lara", text)
        self.assertIn("ORIN Joias", text)
        self.assertIn("nome", text.lower())
        self.assertNotIn("Teste orin", text)
        self.assertIsNone(result["state"].get("confirmed_name"))

    def test_name_after_greeting_moves_to_discovery(self):
        first = run_turn("Boa noite")
        second = run_turn("Jhonatan", first["state"])

        self.assertEqual(second["intent"], "discovery")
        self.assertEqual(second["conversation_stage"], "descoberta")
        self.assertEqual(second["state"]["confirmed_name"], "Jhonatan")
        text = "\n".join(second["reply_blocks"])
        self.assertIn("Jhonatan", text)
        self.assertIn("buscando", text.lower())
        self.assertNotIn("qual é o seu nome", text.lower())

    def test_explicit_name_sentence_extracts_real_name_only(self):
        result = run_turn("Meu nome é Guilherme", {"conversation_stage": "identificacao"})

        self.assertEqual(result["intent"], "discovery")
        self.assertEqual(result["state"]["confirmed_name"], "Guilherme")
        self.assertNotEqual(result["state"]["confirmed_name"], "Meu")
        self.assertNotEqual(result["state"]["confirmed_name"], "Meu Nome")
        self.assertIn("Perfeito, Guilherme.", result["reply_blocks"])

    def test_same_session_keeps_state_without_manual_state_payload(self):
        session_id = "wa:+5547999991111"
        first = run_turn("Jhonatan", {"conversation_stage": "identificacao"}, session_id=session_id)
        second = run_turn("qro agenda uma vizta", session_id=session_id)

        self.assertEqual(first["conversation_stage"], "descoberta")
        self.assertEqual(second["intent"], "appointment")
        self.assertEqual(second["conversation_stage"], "agenda_slots")
        self.assertEqual(second["state"]["confirmed_name"], "Jhonatan")

    def test_greeting_words_are_never_saved_as_name(self):
        for message in ["Oi", "Oii", "Bom dia", "Boa tarde", "Boa noite", "ok", "sim"]:
            with self.subTest(message=message):
                result = run_turn(message)
                self.assertIsNone(result["state"].get("confirmed_name"))
                self.assertEqual(result["conversation_stage"], "identificacao")

    def test_typo_appointment_intent_is_understood_after_name(self):
        state = run_turn("Camila", {"conversation_stage": "identificacao"})["state"]
        result = run_turn("qro agenda uma vizta", state)

        self.assertEqual(result["intent"], "appointment")
        self.assertEqual(result["conversation_stage"], "agenda_slots")
        self.assertEqual(result["next_action"], "check_availability")
        self.assertIn("available_slots", result["missing_fields"])

    def test_available_slots_are_presented_without_creating_booking(self):
        state = run_turn("Camila", {"conversation_stage": "identificacao"})["state"]
        slots = [
            {"date": "2026-07-03", "label": "03/07", "time": "09:00"},
            {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
        ]
        result = run_turn("quero atendimento presencial", state, available_slots=slots)

        self.assertEqual(result["conversation_stage"], "agenda_slots")
        self.assertEqual(result["next_action"], "reply")
        self.assertEqual(result["state"]["last_offered_slots"], slots)
        self.assertIn("09:00", "\n".join(result["reply_blocks"]))
        self.assertNotEqual(result["next_action"], "create_appointment")

    def test_selected_slot_requires_appointment_reason_before_create(self):
        state = run_turn("Camila", {"conversation_stage": "identificacao"})["state"]
        slots = [
            {"date": "2026-07-03", "label": "03/07", "time": "09:00"},
            {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
        ]
        state["conversation_stage"] = "agenda_slots"
        state["last_offered_slots"] = slots

        result = run_turn("Pode ser as 10 horas", state)

        self.assertEqual(result["conversation_stage"], "agenda_contexto")
        self.assertEqual(result["next_action"], "reply")
        self.assertEqual(result["state"]["pending_booking"]["time"], "10:00")
        self.assertIn("motivo", "\n".join(result["reply_blocks"]).lower())

    def test_reason_collects_details_and_asks_confirmation_before_create(self):
        state = {
            "conversation_stage": "agenda_contexto",
            "confirmed_name": "Camila",
            "phone": "+5547999990000",
            "pending_booking": {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
        }

        result = run_turn("quero ver alianças de casamento com gravação", state)

        self.assertEqual(result["conversation_stage"], "agenda_resumo_confirmacao")
        self.assertEqual(result["next_action"], "reply")
        self.assertIn("alianças de casamento", result["state"]["collected_context"]["appointment_reason"])
        self.assertIn("confirma", "\n".join(result["reply_blocks"]).lower())

    def test_confirmation_creates_appointment_payload_and_uses_correct_address(self):
        state = {
            "conversation_stage": "agenda_resumo_confirmacao",
            "confirmed_name": "Camila",
            "phone": "+5547999990000",
            "pending_booking": {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
            "collected_context": {
                "appointment_reason": "alianças de casamento com gravação",
                "interest": "alianças de casamento",
            },
        }

        result = run_turn("confirmado", state)

        self.assertEqual(result["conversation_stage"], "agenda_criar")
        self.assertEqual(result["next_action"], "create_appointment")
        self.assertEqual(result["tool_payload"]["appointment"]["time"], "10:00")
        self.assertIn("alianças de casamento", result["tool_payload"]["appointment"]["notes"])
        self.assertIn("Av. Brasil, 1500", "\n".join(result["reply_blocks"]))

    def test_qa_mode_never_authorizes_real_side_effects(self):
        state = {
            "conversation_stage": "agenda_resumo_confirmacao",
            "confirmed_name": "Camila",
            "phone": "+5547999990000",
            "pending_booking": {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
            "collected_context": {
                "appointment_reason": "alianças de casamento com gravação",
                "interest": "alianças de casamento",
            },
        }

        result = run_turn("confirmado", state, qa_mode=True)

        self.assertEqual(result["next_action"], "simulate_appointment")
        self.assertFalse(result["side_effects"]["send_whatsapp"])
        self.assertFalse(result["side_effects"]["create_appointment"])
        self.assertFalse(result["side_effects"]["update_crm"])

    def test_human_takeover_blocks_automatic_reply(self):
        state = {
            "conversation_stage": "descoberta",
            "confirmed_name": "Camila",
            "human_takeover": True,
        }

        result = run_turn("quero agendar uma visita", state)

        self.assertEqual(result["intent"], "human_takeover")
        self.assertEqual(result["next_action"], "none")
        self.assertEqual(result["reply_blocks"], [])
        self.assertTrue(result["safety"]["needs_human"])


class LaraRootConsoleTest(unittest.TestCase):
    def test_unknown_slash_command_never_becomes_free_mode(self):
        parsed = parse_root_command("/rest")

        self.assertTrue(parsed["is_command"])
        self.assertFalse(parsed["known"])
        self.assertEqual(parsed["error"], "unknown_command")

        result = apply_root_command("/rest", {})

        self.assertEqual(result["type"], "root_error")
        self.assertNotEqual(result["type"], "root_free_text")
        self.assertIn("Comando não reconhecido.", result["reply_blocks"])

    def test_reset_requires_exact_strong_confirmation(self):
        pending = apply_root_command("/reset", {})

        self.assertEqual(pending["type"], "root_reset_pending")
        self.assertEqual(pending["state_patch"]["pending_action"], "reset")
        self.assertIn("CONFIRMAR RESET", "\n".join(pending["reply_blocks"]))

        weak = apply_root_command("sim", {"pending_action": "reset"})

        self.assertNotEqual(weak["type"], "root_reset_confirmed")

        confirmed = apply_root_command("CONFIRMAR RESET", {"pending_action": "reset"})

        self.assertEqual(confirmed["type"], "root_reset_confirmed")
        self.assertTrue(confirmed["state_patch"]["config_reset"])

    def test_reset_can_be_cancelled_without_config_change(self):
        cancelled = apply_root_command("cancelar", {"pending_action": "reset"})

        self.assertEqual(cancelled["type"], "root_reset_cancelled")
        self.assertNotIn("config_reset", cancelled["state_patch"])

    def test_config_command_creates_draft_instead_of_direct_save(self):
        result = apply_root_command("/regra responder em blocos curtos", {})

        self.assertEqual(result["type"], "root_draft_created")
        self.assertEqual(result["state_patch"]["draft"]["status"], "pending_confirmation")
        self.assertEqual(result["state_patch"]["draft"]["command"], "/regra")

    def test_assumir_and_devolver_patch_human_takeover(self):
        started = apply_root_command("/assumir 4796963593", {})
        finished = apply_root_command("/devolver 4796963593", {})

        self.assertEqual(started["type"], "root_takeover_started")
        self.assertTrue(started["state_patch"]["conversation_patch"]["human_takeover"])
        self.assertEqual(started["state_patch"]["target_phone"], "+554796963593")

        self.assertEqual(finished["type"], "root_takeover_finished")
        self.assertFalse(finished["state_patch"]["conversation_patch"]["human_takeover"])


if __name__ == "__main__":
    unittest.main()
