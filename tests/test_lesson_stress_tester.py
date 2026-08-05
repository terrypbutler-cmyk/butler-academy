import importlib.util
import sys
import types
import unittest


if "streamlit" not in sys.modules and importlib.util.find_spec("streamlit") is None:
    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.session_state = {}
    streamlit_stub.secrets = {}
    streamlit_errors_stub = types.ModuleType("streamlit.errors")
    streamlit_errors_stub.StreamlitSecretNotFoundError = type(
        "StreamlitSecretNotFoundError",
        (Exception,),
        {},
    )
    sys.modules["streamlit"] = streamlit_stub
    sys.modules["streamlit.errors"] = streamlit_errors_stub

if "google" not in sys.modules and importlib.util.find_spec("google") is None:
    google_stub = types.ModuleType("google")
    google_genai_stub = types.ModuleType("google.genai")
    google_genai_stub.Client = type("Client", (), {})
    google_stub.genai = google_genai_stub
    sys.modules["google"] = google_stub
    sys.modules["google.genai"] = google_genai_stub

from modules import lesson_stress_tester


class LessonPredictionTests(unittest.TestCase):
    def test_prompt_treats_responses_as_predictions_and_allows_idk(self):
        prompt = lesson_stress_tester.build_lesson_prediction_prompt(
            "Model equivalent fractions, then ask pupils to explain.",
            "- Alex: confidence 24/100; hesitant on cold call",
            30,
            "Year 7",
            "Maths",
            "11 to 12 years old",
            "Key Stage 3 (KS3)",
        )
        compact_prompt = " ".join(prompt.split())

        self.assertIn("profile-informed prediction", compact_prompt)
        self.assertIn("not observed evidence", compact_prompt)
        self.assertIn('"I don\'t know"', prompt)
        self.assertIn('"Probable"', prompt)
        self.assertIn('"Possible"', prompt)
        self.assertIn('"live_check"', prompt)
        self.assertNotIn("predicted_mastery_count", prompt)

    def test_invented_pupil_predictions_are_removed(self):
        result = lesson_stress_tester.normalise_lesson_prediction_result(
            {
                "metrics": {},
                "audit": {},
                "risk_register": [],
                "profile_predictions": [
                    {"name": "Alex", "most_likely_response": "Not sure."},
                    {"name": "Invented", "most_likely_response": "Correct."},
                ],
                "priority_actions": [],
            },
            ["Alex", "Sam"],
        )

        self.assertEqual(
            [entry["name"] for entry in result["profile_predictions"]],
            ["Alex"],
        )


if __name__ == "__main__":
    unittest.main()
