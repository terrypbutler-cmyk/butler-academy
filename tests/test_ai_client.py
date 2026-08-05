import unittest

from PIL import Image

from config import (
    ANALYSIS_MODEL,
    OPENAI_ANALYSIS_MODEL,
    OPENAI_REACTION_MODEL,
    REACTION_MODEL,
)
from modules import ai_client


class AiClientTests(unittest.TestCase):
    def tearDown(self):
        ai_client._provider = ai_client.GEMINI_PROVIDER
        ai_client._gemini_client = None
        ai_client._openai_client = None

    def test_openai_adapter_maps_interactive_model_and_image(self):
        captured = {}

        class FakeResponses:
            def create(self, **kwargs):
                captured.update(kwargs)
                return type("Response", (), {"output_text": '{"ok": true}'})()

        fake_client = type("Client", (), {"responses": FakeResponses()})()
        ai_client._provider = ai_client.OPENAI_PROVIDER
        ai_client._openai_client = fake_client

        response = ai_client.GenerativeModel(REACTION_MODEL).generate_content(
            ["Inspect this", Image.new("RGB", (2, 2), "white")],
            generation_config={"response_mime_type": "application/json"},
        )

        self.assertEqual(response.text, '{"ok": true}')
        self.assertTrue(response.parts)
        self.assertEqual(captured["model"], OPENAI_REACTION_MODEL)
        self.assertEqual(captured["reasoning"], {"effort": "low"})
        self.assertEqual(
            captured["text"],
            {
                "verbosity": "low",
                "format": {"type": "json_object"},
            },
        )
        self.assertFalse(captured["store"])
        content = captured["input"][0]["content"]
        self.assertEqual(content[0], {"type": "input_text", "text": "Inspect this"})
        self.assertTrue(content[1]["image_url"].startswith("data:image/png;base64,"))

    def test_openai_adapter_uses_flagship_model_for_analysis(self):
        captured = {}

        class FakeResponses:
            def create(self, **kwargs):
                captured.update(kwargs)
                return type("Response", (), {"output_text": "analysis"})()

        ai_client._provider = ai_client.OPENAI_PROVIDER
        ai_client._openai_client = type(
            "Client", (), {"responses": FakeResponses()}
        )()

        ai_client.GenerativeModel(ANALYSIS_MODEL).generate_content("Analyse this")

        self.assertEqual(captured["model"], OPENAI_ANALYSIS_MODEL)
        self.assertEqual(captured["reasoning"], {"effort": "medium"})
        self.assertEqual(captured["text"], {"verbosity": "medium"})

    def test_gemini_adapter_preserves_existing_request_shape(self):
        captured = {}

        class FakeModels:
            def generate_content(self, **kwargs):
                captured.update(kwargs)
                return "gemini response"

        ai_client._provider = ai_client.GEMINI_PROVIDER
        ai_client._gemini_client = type(
            "Client", (), {"models": FakeModels()}
        )()

        response = ai_client.GenerativeModel("gemini-test").generate_content(
            ["prompt"],
            generation_config={"response_mime_type": "application/json"},
        )

        self.assertEqual(response, "gemini response")
        self.assertEqual(
            captured,
            {
                "model": "gemini-test",
                "contents": ["prompt"],
                "config": {"response_mime_type": "application/json"},
            },
        )


if __name__ == "__main__":
    unittest.main()
