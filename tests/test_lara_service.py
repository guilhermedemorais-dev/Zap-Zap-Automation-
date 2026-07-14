import unittest

from fastapi.testclient import TestClient

from lara_langgraph.service import app


class LaraServiceTest(unittest.TestCase):
    def test_turn_endpoint_exposes_side_effect_contract(self):
        client = TestClient(app)

        response = client.post(
            "/v1/lara/turn",
            json={
                "session_id": "wa:+5547999997777",
                "phone": "+5547999997777",
                "profile_name": "Perfil ignorado",
                "message": "Boa noite",
                "qa_mode": True,
                "state": {},
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "identification")
        self.assertIn("side_effects", data)
        self.assertFalse(data["side_effects"]["send_whatsapp"])
        self.assertFalse(data["side_effects"]["create_appointment"])
        self.assertFalse(data["side_effects"]["update_crm"])


if __name__ == "__main__":
    unittest.main()
