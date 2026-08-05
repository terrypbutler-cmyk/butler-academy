import types
import unittest
import importlib.util
import json
import sys
from unittest.mock import patch

import pandas as pd

STREAMLIT_AVAILABLE = (
    "streamlit" not in sys.modules
    and importlib.util.find_spec("streamlit") is not None
)

if not STREAMLIT_AVAILABLE and "streamlit" not in sys.modules:
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

from modules import academic_responses, app_shell
from modules.app_shell import normalise_teacher_display_name
from modules.reaction_engine import ReactionSettings


class AcademicAflMemoryTests(unittest.TestCase):
    def setUp(self):
        self.fake_streamlit = types.SimpleNamespace(session_state={})
        self.streamlit_patch = patch.object(
            academic_responses,
            "st",
            self.fake_streamlit,
        )
        self.streamlit_patch.start()

    def tearDown(self):
        self.streamlit_patch.stop()

    def test_discussion_remembers_multiple_students_in_order(self):
        academic_responses._append_afl_comment(
            "teacher",
            "Sir",
            "What do you think of Alex's answer?",
        )
        academic_responses._append_afl_comment(
            "student",
            "Alex",
            "I multiplied by two.",
        )
        academic_responses._append_afl_comment(
            "student",
            "Sam",
            "I agree with Alex, but the units are missing.",
        )

        transcript = academic_responses._afl_transcript()

        self.assertEqual(
            transcript.splitlines(),
            [
                "Sir: What do you think of Alex's answer?",
                "Alex: I multiplied by two.",
                "Sam: I agree with Alex, but the units are missing.",
            ],
        )

    def test_opening_question_marker_includes_the_teacher_identity(self):
        first_add = academic_responses._record_opening_question(
            "Mr Smith",
            "What do you notice?",
        )
        duplicate_add = academic_responses._record_opening_question(
            "Mr Smith",
            "What do you notice?",
        )
        new_teacher_add = academic_responses._record_opening_question(
            "Ms Jones",
            "What do you notice?",
        )

        self.assertTrue(first_add)
        self.assertFalse(duplicate_add)
        self.assertTrue(new_teacher_add)
        self.assertEqual(
            academic_responses._afl_transcript().splitlines(),
            [
                "Mr Smith: What do you notice?",
                "Ms Jones: What do you notice?",
            ],
        )

    def test_marked_whiteboard_answer_is_not_added_twice(self):
        first_add = academic_responses._append_afl_comment(
            "student",
            "Alex",
            "42",
            source="whiteboard",
            marker="whiteboard::question::Alex",
        )
        second_add = academic_responses._append_afl_comment(
            "student",
            "Alex",
            "42",
            source="whiteboard",
            marker="whiteboard::question::Alex",
        )

        self.assertTrue(first_add)
        self.assertFalse(second_add)
        self.assertEqual(
            academic_responses._afl_transcript(),
            "Alex [written answer]: 42",
        )

    def test_listen_in_stays_private_until_feedback_is_shared(self):
        private_result = academic_responses._remember_peer_result_for_class(
            "conversation",
            "Table 1 feedback",
            "We think the force is balanced.",
            "group_discussion",
            "table-1|science|question",
        )

        self.assertFalse(private_result)
        self.assertEqual(academic_responses._afl_transcript(), "")

        shared_result = academic_responses._remember_peer_result_for_class(
            "feedback",
            "Table 1 feedback",
            "We think the force is balanced.",
            "group_discussion",
            "table-1|science|question",
        )

        self.assertTrue(shared_result)
        self.assertEqual(
            academic_responses._afl_transcript(),
            "Table 1 feedback: We think the force is balanced.",
        )

    def test_short_model_output_is_automatically_continued(self):
        participant_df = pd.DataFrame(
            [
                {
                    "Full Name": "Alex",
                    "Peer Discussion Style": "Takes control",
                    "Participation Level": 88,
                    "Academic Confidence": 75,
                    "Independence": 55,
                    "Projected Grade": "6",
                },
                {
                    "Full Name": "Sam",
                    "Peer Discussion Style": "Hesitant listener",
                    "Participation Level": 29,
                    "Academic Confidence": 32,
                    "Independence": 50,
                    "Projected Grade": "4",
                },
            ]
        )

        first_four = {
            "turns": [
                {"speaker": "Alex", "dialogue": "I think it is because of friction."},
                {"speaker": "Sam", "dialogue": "Maybe, I'm not sure."},
                {"speaker": "Alex", "dialogue": "It definitely slows it down."},
                {"speaker": "Sam", "dialogue": "What about the surface?"},
            ],
            "feedback": "We think friction slows it down.",
        }
        next_four = {
            "turns": [
                {"speaker": "Alex", "dialogue": "A rough surface has more friction."},
                {"speaker": "Alex", "dialogue": "So that proves my point."},
                {"speaker": "Sam", "dialogue": "Unless the force is balanced?"},
                {"speaker": "Alex", "dialogue": "We should include that uncertainty."},
            ],
            "feedback": "We think friction changes motion, but forces may balance.",
        }

        class FakeModel:
            def __init__(self):
                self.responses = iter((first_four, next_four))
                self.call_count = 0

            def generate_content(self, *_args, **_kwargs):
                self.call_count += 1
                return types.SimpleNamespace(
                    text=json.dumps(next(self.responses))
                )

        fake_model = FakeModel()
        with (
            patch.object(
                academic_responses.genai,
                "GenerativeModel",
                return_value=fake_model,
            ),
            patch.object(academic_responses.random, "randint", return_value=8),
        ):
            result = academic_responses.generate_peer_discussion(
                "How does friction affect motion?",
                participant_df,
                "Year 7",
                "Science",
                "Sir",
                "turn_and_talk",
            )

        self.assertEqual(fake_model.call_count, 2)
        self.assertEqual(result["target_turns"], 8)
        self.assertEqual(len(result["turns"]), 8)

    def test_refresh_clears_afl_work_but_keeps_voice_preference(self):
        self.fake_streamlit.session_state.update(
            {
                "afl_discussion": [{"role": "student", "content": "An answer"}],
                "afl_started_interactions": ["cold-call::Alex::Question"],
                "afl_exit_answers": {"answers": {"Alex": "An answer"}},
                "afl_teacher_question": "Question",
                "afl_resource_upload": object(),
                "afl_strategy": "Cold Call",
                "afl_cold_call_student": "Alex",
                "wb_answers": {"Alex": "42"},
                "wb_probe_selected": "Alex",
                "hu_volunteers": ["Alex"],
                "hu_selected": "Alex",
                "latest_audio": b"audio",
                "afl_peer_turn_and_talk_result": {"feedback": "A summary"},
                "afl_peer_group_discussion_selection": "Table 1",
                "probe_chat_Alex": [{"role": "student", "content": "Old"}],
                "afl_voice_toggle": False,
            }
        )

        academic_responses._reset_academic_afl_state()

        self.assertEqual(
            self.fake_streamlit.session_state,
            {"afl_voice_toggle": False},
        )

    def test_year_10_voice_keeps_identity_with_a_subtler_cadence(self):
        year_7 = academic_responses._voice_settings_for_cohort("Year 7")
        year_10 = academic_responses._voice_settings_for_cohort("Year 10")

        self.assertEqual(year_7["similarity_boost"], year_10["similarity_boost"])
        self.assertEqual(year_7["style"], year_10["style"])
        self.assertEqual(year_7["speed"], 1.0)
        self.assertEqual(year_10["speed"], 0.96)
        self.assertGreater(year_10["stability"], year_7["stability"])

    def test_explicit_student_voice_is_preserved(self):
        row = {
            "Full Name": "Alex A.",
            "Voice Name": "explicit-voice-id",
        }

        self.assertEqual(
            academic_responses.get_student_voice_id(row),
            "explicit-voice-id",
        )

    def test_missing_voice_column_uses_safe_default(self):
        voice_id = academic_responses.get_student_voice_id(
            {"Full Name": "Alex A."}
        )

        self.assertEqual(
            voice_id,
            academic_responses.DEFAULT_STUDENT_VOICE_ID,
        )


class TeacherAddressOptionTests(unittest.TestCase):
    def setUp(self):
        self.fake_streamlit = types.SimpleNamespace(
            session_state={
                "teacher_display_name": "Mr Butler",
                "teacher_allow_alternative_address": True,
                "teacher_alternative_address": "Sir",
            }
        )
        self.streamlit_patch = patch.object(
            app_shell,
            "st",
            self.fake_streamlit,
        )
        self.streamlit_patch.start()

    def tearDown(self):
        self.streamlit_patch.stop()

    def test_alternative_address_allows_name_or_sir(self):
        self.assertEqual(
            app_shell.get_teacher_address_options(),
            ("Mr Butler", "Sir"),
        )
        instruction = app_shell.get_teacher_address_instruction()
        self.assertIn('"Mr Butler"', instruction)
        self.assertIn('"Sir"', instruction)
        self.assertIn("Vary these across pupils and responses", instruction)

    def test_disabled_alternative_uses_recorded_name_only(self):
        self.fake_streamlit.session_state[
            "teacher_allow_alternative_address"
        ] = False

        self.assertEqual(
            app_shell.get_teacher_address_options(),
            ("Mr Butler",),
        )


class AcademicResponseCalibrationTests(unittest.TestCase):
    def test_teacher_display_name_is_cleaned_and_has_a_safe_fallback(self):
        self.assertEqual(
            normalise_teacher_display_name("  Ms   Patel \n "),
            "Ms Patel",
        )
        self.assertEqual(normalise_teacher_display_name(""), "Teacher")

    def test_attainment_estimate_uses_subject_grade_and_learning_metrics(self):
        high_attaining = pd.Series(
            {
                "Full Name": "High",
                "Maths Predicted Grade": "8",
                "Academic Confidence": 82,
                "Independence": 86,
            }
        )
        developing = pd.Series(
            {
                "Full Name": "Developing",
                "Maths Predicted Grade": "2",
                "Academic Confidence": 31,
                "Independence": 28,
            }
        )

        self.assertGreater(
            academic_responses._student_attainment_score(
                high_attaining,
                "Maths",
            ),
            academic_responses._student_attainment_score(
                developing,
                "Maths",
            ),
        )

    def test_answer_security_control_changes_likely_answer_security(self):
        neutral = pd.Series(
            {
                "Full Name": "Alex",
                "Maths Predicted Grade": "5",
                "Academic Confidence": 55,
                "Independence": 55,
            }
        )
        neutral_score = academic_responses._student_attainment_score(
            neutral,
            "Maths",
        )
        self.assertLess(
            academic_responses._student_attainment_score(
                neutral,
                "Maths",
                ReactionSettings(answer_security=-2),
            ),
            neutral_score,
        )
        self.assertGreater(
            academic_responses._student_attainment_score(
                neutral,
                "Maths",
                ReactionSettings(answer_security=2),
            ),
            neutral_score,
        )

    def test_whole_class_calibration_guarantees_diagnosable_errors(self):
        pupils = pd.DataFrame(
            [
                {
                    "Full Name": f"Pupil {index}",
                    "Maths Predicted Grade": str(2 + index % 7),
                    "Academic Confidence": 30 + index * 6,
                    "Independence": 34 + index * 5,
                }
                for index in range(12)
            ]
        )

        plans = academic_responses.build_response_calibration(
            "Expand and simplify 3(x + 4) - 2x.",
            pupils,
            "Maths",
        )
        substantive_errors = [
            plan
            for plan in plans
            if plan["outcome"] in {"misconception", "slip"}
        ]

        self.assertEqual(len(plans), len(pupils))
        self.assertGreaterEqual(
            len(substantive_errors),
            (len(pupils) + 3) // 4,
        )

    def test_low_readiness_class_can_include_an_authentic_idk_prediction(self):
        pupils = pd.DataFrame(
            [
                {
                    "Full Name": f"Pupil {index}",
                    "Maths Predicted Grade": "2",
                    "Academic Confidence": 16 + index,
                    "Participation Level": 10 + index,
                    "Independence": 18 + index,
                    "Processing Speed": 20 + index,
                    "Cold Call Response": "Reluctant and often says I don't know",
                }
                for index in range(12)
            ]
        )

        plans = academic_responses.build_response_calibration(
            "Explain why dividing by a fraction changes the value.",
            pupils,
            "Maths",
        )

        no_attempts = [
            plan for plan in plans if plan["outcome"] == "no_attempt"
        ]
        self.assertTrue(no_attempts)
        self.assertTrue(
            all(
                plan["likelihood"] in {"probable", "possible"}
                for plan in plans
            )
        )
        calibration, _ = academic_responses._format_response_calibration(
            plans,
            "Maths",
        )
        self.assertIn("NO_ATTEMPT", calibration)
        self.assertIn("I don't know", calibration)

    def test_same_pupil_and_question_keep_a_consistent_knowledge_state(self):
        pupil = pd.DataFrame(
            [
                {
                    "Full Name": "Alex",
                    "English Predicted Grade": "5",
                    "Academic Confidence": 48,
                    "Independence": 52,
                }
            ]
        )

        first = academic_responses.build_response_calibration(
            "How does the writer present tension in this extract?",
            pupil,
            "English",
        )
        second = academic_responses.build_response_calibration(
            "How does the writer present tension in this extract?",
            pupil,
            "English",
        )

        self.assertEqual(first, second)

    def test_discussion_dynamics_use_spreadsheet_style_and_focus_data(self):
        pair = pd.DataFrame(
            [
                {
                    "Full Name": "Alex",
                    "Peer Discussion Style": "Takes control and answers for others",
                    "Participation Level": 91,
                    "Academic Confidence": 84,
                    "Independence": 35,
                    "Typical Learning Barrier": "Loses focus and needs redirection",
                    "Preferred Peers": "Sam",
                },
                {
                    "Full Name": "Sam",
                    "Peer Discussion Style": "Quiet listener; hesitant to contribute",
                    "Participation Level": 24,
                    "Academic Confidence": 27,
                    "Independence": 52,
                    "Preferred Peers": "Alex",
                },
            ]
        )

        dynamics = academic_responses.build_discussion_dynamics(
            pair,
            "turn_and_talk",
        )
        patterns = {
            pupil["name"]: pupil["pattern"]
            for pupil in dynamics["pupils"]
        }

        self.assertEqual(patterns["Alex"], "monopolises")
        self.assertEqual(patterns["Sam"], "reluctant")
        self.assertEqual(dynamics["off_task_level"], "likely")
        self.assertGreater(dynamics["minimum_turns"], 4)
        self.assertGreater(dynamics["maximum_turns"], 4)

    def test_focused_balanced_pair_is_not_forced_off_task(self):
        pair = pd.DataFrame(
            [
                {
                    "Full Name": "A",
                    "Peer Discussion Style": "Collaborative and supportive",
                    "Participation Level": 62,
                    "Academic Confidence": 61,
                    "Independence": 72,
                },
                {
                    "Full Name": "B",
                    "Peer Discussion Style": "Builds on other answers",
                    "Participation Level": 66,
                    "Academic Confidence": 64,
                    "Independence": 75,
                },
            ]
        )

        dynamics = academic_responses.build_discussion_dynamics(
            pair,
            "turn_and_talk",
        )

        self.assertEqual(dynamics["off_task_level"], "unlikely")
        self.assertTrue(
            all(
                pupil["pattern"] == "balanced"
                for pupil in dynamics["pupils"]
            )
        )


@unittest.skipUnless(STREAMLIT_AVAILABLE, "Streamlit is not installed")
class AcademicAflAppTests(unittest.TestCase):
    def test_cold_call_students_share_memory_until_refresh(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_string(
            """
import pandas as pd
import streamlit as st
from modules import academic_responses

academic_responses.get_secret = lambda _name: "test-key"
academic_responses.display_student_photo = lambda *_args, **_kwargs: None
st.session_state.teacher_display_name = "Mr Smith"

def fake_answers(_question, student_subset, *_args, **_kwargs):
    name = student_subset.iloc[0]["Full Name"]
    replies = {
        "Alex": "I think the answer is 8.",
        "Sam": "I agree with Alex, but I would explain the multiplication.",
    }
    return {name: replies[name]}

academic_responses.fetch_ai_answers = fake_answers
academic_responses.generate_discussion_reply = (
    lambda target_name, *_args, **_kwargs:
    (f"{target_name} builds on the earlier answer.", "eager")
)

students = pd.DataFrame(
    [
        {"Full Name": "Alex", "Projected Grade": "5", "SEN Status": ""},
        {"Full Name": "Sam", "Projected Grade": "6", "SEN Status": ""},
    ]
)
academic_responses.render_academic_responses(
    students,
    "Year 7",
    "Maths",
)
"""
        )
        app.run()
        app.toggle[0].set_value(False)
        app.text_area[0].set_value("What is four multiplied by two?")
        app.radio[0].set_value("🎯 Cold Call (Interactive Probing)")
        app.run()

        ask_alex = next(
            button
            for button in app.button
            if "Ask Alex" in button.label
        )
        ask_alex.click()
        app.run()

        app.selectbox[0].set_value("Sam")
        app.run()
        invite_sam = next(
            button
            for button in app.button
            if "Invite Sam" in button.label
        )
        invite_sam.click()
        app.run()

        comments = app.session_state["afl_discussion"]
        self.assertEqual(
            [(entry["speaker"], entry["content"]) for entry in comments],
            [
                ("Mr Smith", "What is four multiplied by two?"),
                ("Alex", "I think the answer is 8."),
                (
                    "Sam",
                    "I agree with Alex, but I would explain the multiplication.",
                ),
            ],
        )

        refresh = next(
            button
            for button in app.button
            if button.label == "🔄 Refresh session"
        )
        refresh.click()
        app.run()

        self.assertEqual(app.session_state["afl_discussion"], [])
        self.assertEqual(app.text_area[0].value, "")


if __name__ == "__main__":
    unittest.main()
