import importlib.util
import random
import sys
import types
import unittest

import pandas as pd


if "streamlit" not in sys.modules and importlib.util.find_spec("streamlit") is None:
    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.session_state = {}
    streamlit_stub.secrets = {}
    streamlit_stub.cache_data = lambda **_kwargs: (lambda function: function)
    streamlit_errors_stub = types.ModuleType("streamlit.errors")
    streamlit_errors_stub.StreamlitSecretNotFoundError = type(
        "StreamlitSecretNotFoundError",
        (Exception,),
        {},
    )
    sys.modules["streamlit"] = streamlit_stub
    sys.modules["streamlit.errors"] = streamlit_errors_stub

if "elevenlabs" not in sys.modules and importlib.util.find_spec("elevenlabs") is None:
    elevenlabs_stub = types.ModuleType("elevenlabs")
    elevenlabs_client_stub = types.ModuleType("elevenlabs.client")
    elevenlabs_stub.VoiceSettings = type(
        "VoiceSettings",
        (),
        {"__init__": lambda self, **kwargs: self.__dict__.update(kwargs)},
    )
    elevenlabs_client_stub.ElevenLabs = type("ElevenLabs", (), {})
    sys.modules["elevenlabs"] = elevenlabs_stub
    sys.modules["elevenlabs.client"] = elevenlabs_client_stub

if "google" not in sys.modules and importlib.util.find_spec("google") is None:
    google_stub = types.ModuleType("google")
    google_genai_stub = types.ModuleType("google.genai")
    google_genai_stub.Client = type("Client", (), {})
    google_stub.genai = google_genai_stub
    sys.modules["google"] = google_stub
    sys.modules["google.genai"] = google_genai_stub

from modules import observe_learning
from modules.reaction_engine import ReactionSettings


class ObservationBalanceTests(unittest.TestCase):
    def test_temporary_controls_change_state_not_the_source_row(self):
        row = pd.Series(
            {
                "Full Name": "Alex",
                "Participation Level": 60,
                "Academic Confidence": 60,
                "Independence": 60,
                "Processing Speed": 60,
            }
        )
        original = row.copy()

        natural = observe_learning.build_student_observation_state(
            row,
            random.Random(4),
        )
        emphasised_delay = observe_learning.build_student_observation_state(
            row,
            random.Random(4),
            ReactionSettings(processing=-2, independence=-2),
        )

        self.assertEqual(row.to_dict(), original.to_dict())
        self.assertLess(emphasised_delay["work_rate"], natural["work_rate"])
        self.assertGreaterEqual(
            emphasised_delay["decay_rate"],
            natural["decay_rate"],
        )

    def test_send_status_does_not_automatically_reduce_work_readiness(self):
        common = {
            "Full Name": "Alex",
            "Participation Level": 58,
            "Academic Confidence": 54,
            "Independence": 61,
            "Processing Speed": 57,
            "Typical Learning Barrier": "Needs a worked example",
        }
        no_send = pd.Series({**common, "SEN Status": "None"})
        send = pd.Series({**common, "SEN Status": "K"})

        no_send_state = observe_learning.build_student_observation_state(
            no_send,
            random.Random(19),
        )
        send_state = observe_learning.build_student_observation_state(
            send,
            random.Random(19),
        )

        self.assertEqual(
            no_send_state["motivation"],
            send_state["motivation"],
        )
        self.assertEqual(
            no_send_state["decay_rate"],
            send_state["decay_rate"],
        )

    def test_work_questions_outnumber_rare_interruptions(self):
        pupils = pd.DataFrame(
            [
                {
                    "Full Name": f"Pupil {index}",
                    "Participation Level": 38 + index % 40,
                    "Academic Confidence": 35 + index % 45,
                    "Independence": 32 + index % 50,
                    "Processing Speed": 36 + index % 44,
                    "Typical Learning Barrier": (
                        "Easily distracted by nearby conversation"
                        if index < 5
                        else "Needs occasional clarification of instructions"
                    ),
                    "Peer Discussion Style": (
                        "Chatty with friends" if index < 5 else "Collaborative"
                    ),
                }
                for index in range(30)
            ]
        )
        states = {
            row["Full Name"]: observe_learning.build_student_observation_state(
                row,
                random.Random(index),
            )
            for index, (_, row) in enumerate(pupils.iterrows())
        }
        for index in range(5):
            states[f"Pupil {index}"]["motivation"] = 42

        rng = random.Random(2026)
        totals = {
            "work_question": 0,
            "toilet": 0,
            "peer_distraction": 0,
        }
        for scan in range(200):
            events = observe_learning.assign_classroom_events(
                list(states),
                pupils,
                states,
                current_minute=scan * 5,
                rng=rng,
            )
            kinds = [event["kind"] for event in events.values()]
            for kind in kinds:
                totals[kind] += 1
            self.assertLessEqual(kinds.count("toilet"), 1)
            self.assertLessEqual(kinds.count("peer_distraction"), 1)
            self.assertGreaterEqual(kinds.count("work_question"), 2)

        self.assertGreater(
            totals["work_question"],
            totals["toilet"] + totals["peer_distraction"],
        )
        self.assertLess(totals["toilet"], 20)
        self.assertLess(totals["peer_distraction"], 30)

    def test_learning_summary_works_for_an_early_manual_stop(self):
        names = ["Alex", "Sam", "Mina", "Jo"]
        states = {
            "Alex": {
                "progress": 90,
                "motivation": 78,
                "initial_motivation": 68,
                "work_questions": 0,
                "interventions": 1,
                "positive_interventions": 1,
            },
            "Sam": {
                "progress": 75,
                "motivation": 70,
                "initial_motivation": 72,
                "work_questions": 1,
                "interventions": 0,
                "positive_interventions": 0,
            },
            "Mina": {
                "progress": 30,
                "motivation": 48,
                "initial_motivation": 62,
                "work_questions": 2,
                "interventions": 1,
                "positive_interventions": 0,
            },
            "Jo": {
                "progress": 10,
                "motivation": 34,
                "initial_motivation": 55,
                "work_questions": 0,
                "interventions": 0,
                "positive_interventions": 0,
            },
        }
        engagement = {
            "Alex": {"time": "0:20"},
            "Sam": {"time": "0:50"},
            "Mina": {"time": "1:40"},
            "Jo": {"time": "Failed"},
        }
        observations = {
            "Mina": "Mina is rereading the example before attempting the next step.",
            "Jo": "Jo has written a heading but has not begun the first question.",
        }

        summary = observe_learning.build_learning_summary(
            names,
            states,
            engagement,
            observations,
            elapsed_minutes=15,
            planned_minutes=30,
            task="Explain the pattern and complete the examples.",
        )

        self.assertEqual(summary["lesson_fraction"], 50)
        self.assertEqual(summary["average_progress"], 51)
        self.assertEqual(summary["bands"]["substantial"], 2)
        self.assertEqual(summary["bands"]["developing"], 1)
        self.assertEqual(summary["bands"]["limited"], 1)
        self.assertEqual(summary["work_questions"], 3)
        self.assertEqual(summary["interventions"], 2)
        self.assertEqual(summary["standouts"][0]["name"], "Alex")
        self.assertEqual(
            {pupil["name"] for pupil in summary["follow_up"]},
            {"Mina", "Jo"},
        )


if __name__ == "__main__":
    unittest.main()
