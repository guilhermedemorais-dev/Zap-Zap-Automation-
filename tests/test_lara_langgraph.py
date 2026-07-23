import unittest
from pathlib import Path
from itertools import count
from tempfile import TemporaryDirectory

import lara_langgraph.graph as graph_module
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

    def test_generic_hello_does_not_duplicate_tudo_bem(self):
        result = run_turn("Olá")

        self.assertEqual(result["intent"], "identification")
        self.assertIn("Olá, tudo bem?", result["reply_blocks"])
        self.assertNotIn("Olá, tudo bem. Tudo bem?", "\n".join(result["reply_blocks"]))

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

    def test_file_state_store_survives_runtime_cache_clear(self):
        original_file = graph_module.STATE_FILE
        session_id = "wa:+5547999993333"
        try:
            with TemporaryDirectory() as tmpdir:
                graph_module.STATE_FILE = str(Path(tmpdir) / "sessions.json")
                graph_module._SESSION_STATES.clear()
                graph_module._compiled_graph.cache_clear()

                first = run_turn("Guilherme", {"conversation_stage": "identificacao"}, session_id=session_id)
                self.assertEqual(first["state"]["confirmed_name"], "Guilherme")

                graph_module._SESSION_STATES.clear()
                graph_module._compiled_graph.cache_clear()

                second = run_turn("quero agendar", session_id=session_id)

                self.assertEqual(second["state"]["confirmed_name"], "Guilherme")
                self.assertEqual(second["conversation_stage"], "agenda_slots")
                self.assertEqual(second["next_action"], "check_availability")
        finally:
            graph_module.STATE_FILE = original_file
            graph_module._SESSION_STATES.clear()
            graph_module._compiled_graph.cache_clear()

    def test_same_session_does_not_reset_after_greeting_name_and_appointment(self):
        session_id = "wa:+5547999992222"
        first = run_turn("Boa noite", session_id=session_id)
        second = run_turn("Guilherme", session_id=session_id)
        third = run_turn("Fazer um agendamento", session_id=session_id)

        self.assertEqual(first["conversation_stage"], "identificacao")
        self.assertEqual(second["conversation_stage"], "descoberta")
        self.assertEqual(second["state"]["confirmed_name"], "Guilherme")
        self.assertEqual(third["intent"], "appointment")
        self.assertEqual(third["conversation_stage"], "agenda_slots")
        self.assertEqual(third["next_action"], "check_availability")
        self.assertEqual(third["state"]["confirmed_name"], "Guilherme")
        self.assertIn("Perfeito, Guilherme.", "\n".join(third["reply_blocks"]))
        self.assertNotIn("informar seu nome", "\n".join(third["reply_blocks"]).lower())

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

    def test_store_location_question_returns_official_address_without_starting_booking(self):
        state = run_turn("Camila", {"conversation_stage": "identificacao"})["state"]
        result = run_turn("onde fica a loja?", state)

        self.assertEqual(result["intent"], "information")
        self.assertEqual(result["next_action"], "reply")
        text = "\n".join(result["reply_blocks"])
        self.assertIn("Av. Brasil, 1500", text)
        self.assertIn("https://maps.app.goo.gl/geMC3hHsQqGfSnnm6", text)
        self.assertNotEqual(result["next_action"], "check_availability")

    def test_human_request_routes_to_handoff_and_pauses_next_bot_reply(self):
        state = run_turn("Camila", {"conversation_stage": "identificacao"})["state"]
        result = run_turn("quero falar com uma atendente", state)
        follow_up = run_turn("oi", result["state"])

        self.assertEqual(result["intent"], "handoff")
        self.assertEqual(result["next_action"], "handoff")
        self.assertTrue(result["safety"]["needs_human"])
        self.assertTrue(result["state"]["human_takeover"])
        self.assertEqual(follow_up["next_action"], "none")
        self.assertEqual(follow_up["reply_blocks"], [])

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

    def test_selected_slot_accepts_hour_written_in_words(self):
        state = run_turn("Camila", {"conversation_stage": "identificacao"})["state"]
        slots = [
            {"date": "2026-07-03", "label": "03/07", "time": "09:00"},
            {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
            {"date": "2026-07-03", "label": "03/07", "time": "11:00"},
        ]
        state["conversation_stage"] = "agenda_slots"
        state["last_offered_slots"] = slots

        result = run_turn("pode ser as dez", state)

        self.assertEqual(result["conversation_stage"], "agenda_contexto")
        self.assertEqual(result["state"]["pending_booking"]["time"], "10:00")
        self.assertIn("motivo", "\n".join(result["reply_blocks"]).lower())

    def test_reason_collects_details_and_asks_contact_before_confirmation(self):
        state = {
            "conversation_stage": "agenda_contexto",
            "confirmed_name": "Camila",
            "phone": "+5547999990000",
            "pending_booking": {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
        }

        result = run_turn("quero ver alianças de casamento com gravação", state)

        self.assertEqual(result["conversation_stage"], "agenda_tipo_joia")
        self.assertEqual(result["next_action"], "reply")
        self.assertIn("alianças de casamento", result["state"]["collected_context"]["appointment_reason"])
        self.assertIn("pronta", "\n".join(result["reply_blocks"]).lower())
        self.assertIn("personalizada", "\n".join(result["reply_blocks"]).lower())

    def test_vague_appointment_reason_asks_for_more_context(self):
        state = {
            "conversation_stage": "agenda_contexto",
            "confirmed_name": "Camila",
            "phone": "+5547999990000",
            "pending_booking": {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
        }

        result = run_turn("anel", state)

        self.assertEqual(result["conversation_stage"], "agenda_contexto")
        self.assertEqual(result["next_action"], "reply")
        self.assertIn("detalhe", "\n".join(result["reply_blocks"]).lower())
        self.assertNotEqual(result["next_action"], "create_appointment")

    def test_reason_then_contact_details_before_confirmation(self):
        state = {
            "conversation_stage": "agenda_contexto",
            "confirmed_name": "Camila",
            "phone": "+5547999990000",
            "pending_booking": {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
        }

        reason = run_turn("quero ver alianças de casamento com gravação interna", state)
        preference = run_turn("quero uma pronta com nossos nomes gravados", reason["state"])
        contact = run_turn("meu email é camila@example.com e esse WhatsApp está correto", preference["state"])

        self.assertEqual(reason["conversation_stage"], "agenda_tipo_joia")
        self.assertEqual(preference["conversation_stage"], "agenda_contato")
        self.assertIn("e-mail", "\n".join(preference["reply_blocks"]).lower())
        self.assertEqual(contact["conversation_stage"], "agenda_resumo_confirmacao")
        self.assertEqual(contact["next_action"], "reply")
        self.assertEqual(contact["state"]["collected_context"]["customer_email"], "camila@example.com")
        self.assertTrue(contact["state"]["collected_context"]["phone_confirmed"])
        self.assertEqual(contact["state"]["collected_context"]["purchase_preference"], "pronta")
        self.assertIn("confirma", "\n".join(contact["reply_blocks"]).lower())

    def test_initial_reason_with_no_occasion_asks_consultative_details(self):
        state = {
            "conversation_stage": "agenda_contexto",
            "confirmed_name": "Camila",
            "phone": "+5547999990000",
            "pending_booking": {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
        }

        result = run_turn("quero ver anel de noivado", state)

        self.assertEqual(result["conversation_stage"], "agenda_detalhes")
        self.assertEqual(result["next_action"], "reply")
        self.assertIn("momento", "\n".join(result["reply_blocks"]).lower())
        self.assertNotIn("e-mail", "\n".join(result["reply_blocks"]).lower())

    def test_consultative_details_then_purchase_preference_then_contact(self):
        state = {
            "conversation_stage": "agenda_detalhes",
            "confirmed_name": "Camila",
            "phone": "+5547999990000",
            "pending_booking": {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
            "collected_context": {
                "appointment_reason": "quero ver anel de noivado",
                "interest": "anel de noivado",
            },
        }

        details = run_turn("vou pedir minha namorada em casamento no mês que vem", state)
        preference = run_turn("prefiro ver modelos prontos", details["state"])

        self.assertEqual(details["conversation_stage"], "agenda_tipo_joia")
        self.assertIn("pronta", "\n".join(details["reply_blocks"]).lower())
        self.assertEqual(preference["conversation_stage"], "agenda_contato")
        self.assertEqual(preference["state"]["collected_context"]["purchase_preference"], "pronta")
        self.assertIn("e-mail", "\n".join(preference["reply_blocks"]).lower())

    def test_contact_stage_requires_email_before_confirmation(self):
        state = {
            "conversation_stage": "agenda_contato",
            "confirmed_name": "Camila",
            "phone": "+5547999990000",
            "pending_booking": {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
            "collected_context": {
                "appointment_reason": "alianças de casamento com gravação interna",
                "interest": "alianças de casamento",
            },
        }

        result = run_turn("sim, esse WhatsApp está correto", state)

        self.assertEqual(result["conversation_stage"], "agenda_contato")
        self.assertEqual(result["next_action"], "reply")
        self.assertIn("e-mail", "\n".join(result["reply_blocks"]).lower())
        self.assertNotEqual(result["next_action"], "create_appointment")

    def test_confirmation_creates_appointment_payload_and_uses_correct_address(self):
        state = {
            "conversation_stage": "agenda_resumo_confirmacao",
            "confirmed_name": "Camila",
            "phone": "+5547999990000",
            "pending_booking": {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
            "collected_context": {
                "appointment_reason": "alianças de casamento com gravação",
                "interest": "alianças de casamento",
                "customer_email": "camila@example.com",
                "phone_confirmed": True,
                "purchase_preference": "personalizada",
            },
        }

        result = run_turn("confirmado", state)

        self.assertEqual(result["conversation_stage"], "agenda_criar")
        self.assertEqual(result["next_action"], "create_appointment")
        self.assertEqual(result["tool_payload"]["appointment"]["time"], "10:00")
        self.assertEqual(result["tool_payload"]["appointment"]["email"], "camila@example.com")
        self.assertTrue(result["tool_payload"]["appointment"]["phone_confirmed"])
        self.assertIn("alianças de casamento", result["tool_payload"]["appointment"]["notes"])
        self.assertIn("E-mail: camila@example.com", result["tool_payload"]["appointment"]["notes"])
        self.assertIn("WhatsApp confirmado: sim", result["tool_payload"]["appointment"]["notes"])
        self.assertIn("Preferência: personalizada", result["tool_payload"]["appointment"]["notes"])
        self.assertNotIn("Av. Brasil, 1500", "\n".join(result["reply_blocks"]))

    def test_final_confirmation_phrase_does_not_overwrite_visit_reason(self):
        state = {
            "conversation_stage": "agenda_resumo_confirmacao",
            "confirmed_name": "Guilherme",
            "phone": "+5522998911070",
            "pending_booking": {"date": "2026-07-21", "label": "21/07", "time": "09:00"},
            "collected_context": {
                "appointment_reason": "Estou querendo fazer um par de aliança de casamento, então gostaria de saber sobre o catálogo e o tipo ouro vocês têm",
                "interest": "alianças de casamento",
                "customer_email": "guilherme@example.com",
                "phone_confirmed": True,
                "purchase_preference": "personalizada",
            },
        }

        result = run_turn("Sim é isso mesmo", state)

        self.assertEqual(result["conversation_stage"], "agenda_criar")
        self.assertEqual(result["next_action"], "create_appointment")
        payload = result["tool_payload"]["appointment"]
        self.assertEqual(payload["reason"], "Estou querendo fazer um par de aliança de casamento, então gostaria de saber sobre o catálogo e o tipo ouro vocês têm")
        self.assertNotEqual(payload["reason"], "Sim é isso mesmo")
        self.assertIn("alianças de casamento", payload["notes"])
        self.assertNotIn("Para preparar melhor", "\n".join(result["reply_blocks"]))

    def test_rclear_resets_session_instead_of_becoming_appointment_reason(self):
        state = {
            "conversation_stage": "agenda_contexto",
            "confirmed_name": "Guilherme",
            "phone": "+5522998911070",
            "pending_booking": {"date": "2026-07-21", "label": "21/07", "time": "09:00"},
            "collected_context": {
                "appointment_reason": "alianças de casamento",
                "interest": "alianças de casamento",
            },
        }

        result = run_turn("/rclear", state)

        self.assertEqual(result["intent"], "session_clear")
        self.assertEqual(result["conversation_stage"], "inicio")
        self.assertIsNone(result["state"].get("confirmed_name"))
        self.assertIsNone(result["state"].get("pending_booking"))
        self.assertEqual(result["state"].get("collected_context"), {})
        self.assertNotIn("/rclear", result["crm_note"])

    def test_full_appointment_journey_keeps_context_until_create_payload(self):
        first = run_turn("Boa noite")
        self.assertEqual(first["conversation_stage"], "identificacao")
        self.assertIsNone(first["state"].get("confirmed_name"))

        named = run_turn("Guilherme", first["state"])
        self.assertEqual(named["conversation_stage"], "descoberta")
        self.assertEqual(named["state"]["confirmed_name"], "Guilherme")

        request = run_turn("Queria agendar um atendimento na loja", named["state"])
        self.assertEqual(request["next_action"], "check_availability")
        self.assertEqual(request["conversation_stage"], "agenda_slots")

        slots = [
            {"date": "2026-07-27", "label": "27/07 - 09:00", "time": "09:00"},
            {"date": "2026-07-27", "label": "27/07 - 10:00", "time": "10:00"},
            {"date": "2026-07-27", "label": "27/07 - 11:00", "time": "11:00"},
        ]
        listed = run_turn("retorno crm", request["state"], available_slots=slots)
        self.assertEqual(listed["conversation_stage"], "agenda_slots")
        self.assertIn("27/07 - 10:00", "\n".join(listed["reply_blocks"]))

        selected = run_turn("10 horas está ótimo", listed["state"])
        self.assertEqual(selected["conversation_stage"], "agenda_contexto")
        self.assertIn("motivo", "\n".join(selected["reply_blocks"]).lower())

        vague = run_turn("anel", selected["state"])
        self.assertEqual(vague["conversation_stage"], "agenda_contexto")
        self.assertIn("detalhes", "\n".join(vague["reply_blocks"]).lower())

        reason = run_turn("quero ver alianças de casamento com gravação interna", vague["state"])
        self.assertEqual(reason["conversation_stage"], "agenda_tipo_joia")
        self.assertIn("pronta", "\n".join(reason["reply_blocks"]).lower())

        preference = run_turn("quero uma pronta, com meu nome e o da minha esposa escrito dentro da aliança", reason["state"])
        self.assertEqual(preference["conversation_stage"], "agenda_contato")
        self.assertIn("e-mail", "\n".join(preference["reply_blocks"]).lower())

        contact = run_turn("guilherme@example.com, esse WhatsApp está correto", preference["state"])
        self.assertEqual(contact["conversation_stage"], "agenda_resumo_confirmacao")
        summary_text = "\n".join(contact["reply_blocks"])
        self.assertIn("Guilherme", summary_text)
        self.assertIn("27/07 - 10:00", summary_text)
        self.assertIn("alianças de casamento", summary_text)
        self.assertIn("pronta", summary_text)

        create = run_turn("confirmado", contact["state"])
        payload = create["tool_payload"]["appointment"]
        self.assertEqual(create["next_action"], "create_appointment")
        self.assertEqual(payload["name"], "Guilherme")
        self.assertEqual(payload["date"], "2026-07-27")
        self.assertEqual(payload["time"], "10:00")
        self.assertEqual(payload["email"], "guilherme@example.com")
        self.assertEqual(payload["interest"], "alianças de casamento")
        self.assertIn("alianças de casamento", payload["notes"])
        self.assertIn("Preferência: pronta", payload["notes"])
        self.assertNotIn("Olá, tudo bem?", "\n".join(create["reply_blocks"]))
        self.assertNotIn("Av. Brasil, 1500", "\n".join(create["reply_blocks"]))

    def test_confirmation_correction_keeps_contact_data_and_resummarizes(self):
        state = {
            "conversation_stage": "agenda_resumo_confirmacao",
            "confirmed_name": "Camila",
            "phone": "+5547999990000",
            "pending_booking": {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
            "collected_context": {
                "appointment_reason": "alianças de casamento",
                "interest": "alianças de casamento",
                "customer_email": "camila@example.com",
                "phone_confirmed": True,
                "purchase_preference": "pronta",
            },
        }

        result = run_turn("quero acrescentar gravação interna com nossos nomes", state)

        self.assertEqual(result["conversation_stage"], "agenda_resumo_confirmacao")
        self.assertEqual(result["next_action"], "reply")
        self.assertEqual(result["state"]["collected_context"]["customer_email"], "camila@example.com")
        self.assertTrue(result["state"]["collected_context"]["phone_confirmed"])
        self.assertIn("gravação interna", "\n".join(result["reply_blocks"]).lower())
        self.assertNotIn("e-mail", "\n".join(result["reply_blocks"]).lower())

    def test_qa_mode_never_authorizes_real_side_effects(self):
        state = {
            "conversation_stage": "agenda_resumo_confirmacao",
            "confirmed_name": "Camila",
            "phone": "+5547999990000",
            "pending_booking": {"date": "2026-07-03", "label": "03/07", "time": "10:00"},
            "collected_context": {
                "appointment_reason": "alianças de casamento com gravação",
                "interest": "alianças de casamento",
                "customer_email": "camila@example.com",
                "phone_confirmed": True,
                "purchase_preference": "personalizada",
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
