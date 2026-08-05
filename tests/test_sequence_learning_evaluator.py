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

from modules import sequence_learning_evaluator


class FakeUpload:
    def __init__(self, name, data):
        self.name = name
        self._data = data

    def getvalue(self):
        return self._data


class SequenceEvaluatorTests(unittest.TestCase):
    def test_text_sources_preserve_upload_order(self):
        text, images, notes = (
            sequence_learning_evaluator.extract_sequence_sources(
                [
                    FakeUpload("lesson_1.txt", b"Introduce particle models."),
                    FakeUpload("lesson_2.txt", b"Apply the model to changes of state."),
                ],
                "The final endpoint is explaining evaporation.",
            )
        )

        self.assertLess(text.index("lesson_1.txt"), text.index("lesson_2.txt"))
        self.assertIn("final endpoint", text)
        self.assertEqual(images, [])
        self.assertEqual(len(notes), 2)

    def test_prompt_evaluates_learning_across_lessons(self):
        prompt = sequence_learning_evaluator.build_sequence_prompt(
            "Lesson 1: Fractions. Lesson 2: Ratio.",
            "- Alex: confidence 45/100",
            "Year 7",
            "Maths",
            expected_lessons=2,
        )

        self.assertIn("Progression and prerequisites", prompt)
        self.assertIn("Cumulative learning", prompt)
        self.assertIn("Include every detected lesson", prompt)
        self.assertIn("approximately 2 lessons", prompt)
        self.assertIn("profile-informed prediction", prompt)
        self.assertIn('"I don\'t know"', prompt)
        self.assertIn('"response_predictions"', prompt)
        self.assertIn('"validation_plan"', prompt)

    def test_result_scores_and_pupil_names_are_constrained(self):
        result = sequence_learning_evaluator.normalise_sequence_result(
            {
                "metrics": {
                    "lessons_detected": 6,
                    "coherence_score": 140,
                    "progression_score": -5,
                    "retrieval_score": 65,
                    "assessment_score": 50,
                    "class_access_score": 70,
                    "verdict": "Mostly coherent",
                },
                "sequence_map": [],
                "gaps_and_bottlenecks": [],
                "response_predictions": [
                    {
                        "name": "Alex",
                        "most_likely_response": "A partial explanation",
                    },
                    {
                        "name": "Invented Pupil",
                        "most_likely_response": "Unsupported",
                    },
                ],
                "priority_actions": [],
                "validation_plan": [],
            },
            ["Alex", "Sam"],
        )

        self.assertEqual(result["metrics"]["coherence_score"], 100)
        self.assertEqual(result["metrics"]["progression_score"], 0)
        self.assertEqual(
            [
                prediction["name"]
                for prediction in result["response_predictions"]
            ],
            ["Alex"],
        )


if __name__ == "__main__":
    unittest.main()
