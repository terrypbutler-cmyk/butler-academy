import importlib.util
import sys
import types
import unittest
from unittest.mock import patch

import pandas as pd


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

from modules import reaction_engine
from modules.reaction_engine import ReactionSettings, ReactionState


class ReactionEngineTests(unittest.TestCase):
    def setUp(self):
        self.row = pd.Series(
            {
                "Full Name": "Alex",
                "Participation Level": 35,
                "Academic Confidence": 38,
                "Processing Speed": 45,
                "Independence": 42,
                "Cold Call Response": "Hesitant and sometimes says I don't know",
                "Peer Discussion Style": "Quiet listener",
                "SEN Status": "K",
                "EAL Status": "Yes",
                "Disadvantaged (PP)": "Yes",
                "Ethnicity": "Example group",
            }
        )

    def test_demographics_do_not_support_challenge_or_refusal(self):
        supported, evidence = reaction_engine.focus_support(
            self.row,
            "public_challenge",
        )

        self.assertFalse(supported)
        self.assertEqual(evidence, [])

    def test_direct_interaction_evidence_can_support_a_mild_challenge(self):
        row = self.row.copy()
        row["Typical Learning Barrier"] = "Questions instructions when frustrated"

        supported, evidence = reaction_engine.focus_support(
            row,
            "public_challenge",
        )

        self.assertTrue(supported)
        self.assertIn("recorded interaction signal", evidence[0])

    def test_unsupported_focus_is_disclosed_as_hypothetical(self):
        prompt, hypothetical, _ = reaction_engine.build_reaction_prompt(
            self.row,
            "Year 7",
            "Open your book and begin question one.",
            "public instruction",
            ReactionSettings(focus="task_refusal"),
        )

        self.assertTrue(hypothetical)
        self.assertIn("HYPOTHETICAL teaching example", prompt)
        self.assertIn("Do not score, grade", prompt)
        self.assertIn("PP and ethnicity must not be used", prompt)

    def test_result_is_bounded_and_state_advances_one_turn(self):
        result = reaction_engine.normalise_reaction_result(
            {
                "reaction_type": "invented",
                "dialogue": "x" * 500,
                "visible_behaviour": "*looks down*",
                "participation_state": "withdrawn",
                "academic_state": "no_attempt",
                "affect": "angry",
                "began_task": "no",
                "state_summary": "Still waiting.",
            },
            hypothetical=True,
        )

        self.assertEqual(result.reaction_type, "ordinary_engagement")
        self.assertEqual(result.affect, "neutral")
        self.assertIsNone(result.began_task)
        self.assertLessEqual(len(result.dialogue), 360)
        self.assertEqual(result.next_state(ReactionState(turn=3)).turn, 4)

    def test_replay_cache_includes_the_interaction_history(self):
        settings = ReactionSettings()
        state = ReactionState(turn=1)
        first = reaction_engine.reaction_cache_key(
            self.row,
            "What do you think?",
            "academic probe",
            settings,
            state,
            [{"speaker": "Teacher", "text": "Look at the diagram."}],
        )
        second = reaction_engine.reaction_cache_key(
            self.row,
            "What do you think?",
            "academic probe",
            settings,
            state,
            [{"speaker": "Teacher", "text": "Ignore the diagram."}],
        )

        self.assertNotEqual(first, second)

    def test_exact_replay_uses_cached_reaction(self):
        calls = []

        class FakeResponse:
            text = (
                '{"reaction_type":"quiet_non_participation",'
                '"dialogue":"Not sure.","visible_behaviour":"looks down",'
                '"participation_state":"quiet","academic_state":"uncertain",'
                '"affect":"hesitant","began_task":null,'
                '"state_summary":"Waiting after the question."}'
            )

        class FakeModel:
            def generate_content(self, *_args, **_kwargs):
                calls.append(1)
                return FakeResponse()

        cache = {}
        with patch.object(
            reaction_engine.genai,
            "GenerativeModel",
            return_value=FakeModel(),
        ):
            first, _ = reaction_engine.generate_reaction(
                self.row,
                "Year 7",
                "Can you answer?",
                "academic probe",
                ReactionSettings(),
                cache=cache,
            )
            second, _ = reaction_engine.generate_reaction(
                self.row,
                "Year 7",
                "Can you answer?",
                "academic probe",
                ReactionSettings(),
                cache=cache,
            )

        self.assertEqual(first, second)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
