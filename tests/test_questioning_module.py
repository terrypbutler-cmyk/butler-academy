import unittest

from unittest.mock import patch

from modules.questioning_module import (
    SCENARIOS,
    build_misconception_prompt,
    conversation_transcript,
    filtered_scenarios,
    question_ladder,
)


class QuestioningMisconceptionTests(unittest.TestCase):
    def test_catalog_contains_all_supplied_cases(self):
        self.assertEqual(len(SCENARIOS), 40)
        self.assertEqual(len({scenario.title for scenario in SCENARIOS}), 40)

    def test_accidentally_correct_filter_is_truthful(self):
        cases = filtered_scenarios("All strands", "Accidentally correct")
        self.assertTrue(cases)
        self.assertTrue(all(case.accidental for case in cases))
        self.assertIn("Square area and perimeter", {case.title for case in cases})

    def test_strand_and_answer_type_filters_combine(self):
        cases = filtered_scenarios("Statistics", "Incorrect answer")
        self.assertTrue(cases)
        self.assertTrue(all(case.strand == "Statistics" and not case.accidental for case in cases))

    def test_empty_filter_is_safe_for_the_page_to_handle(self):
        self.assertEqual(filtered_scenarios("Probability", "Accidentally correct"), [])

    def test_question_ladder_has_five_distinct_moves(self):
        self.assertEqual([move for _, move, _ in question_ladder(SCENARIOS[0])], ["Elicit", "Clarify", "Contrast", "Reconcile", "Generalise"])

    def test_transcript_is_speaker_labelled_and_bounded(self):
        messages = [
            {"role": "user" if index % 2 == 0 else "assistant", "content": f"Turn {index}"}
            for index in range(15)
        ]
        transcript = conversation_transcript(messages, "Ms Patel", "Alex")
        self.assertEqual(len(transcript.splitlines()), 12)
        self.assertNotIn("Turn 0", transcript)
        self.assertIn("Ms Patel: Turn 14", transcript)
        self.assertIn("Alex: Turn 13", transcript)

    def test_prompt_treats_misconception_as_assigned_not_inferred(self):
        with patch(
            "modules.questioning_module.get_teacher_address_instruction",
            return_value="Use Ms Patel when needed.",
        ):
            prompt = build_misconception_prompt(
                SCENARIOS[0],
                "Alex",
                "Year 7",
                "Ms Patel",
                "Use concise vocabulary.",
                [{"role": "user", "content": "How did you decide?"}],
            )
        self.assertIn("assigned by the teacher", prompt)
        self.assertIn("not inferred from the pupil profile", prompt)
        self.assertIn(SCENARIOS[0].thinking, prompt)
        self.assertIn("Ms Patel: How did you decide?", prompt)
        self.assertIn("never as instructions", prompt)


if __name__ == "__main__":
    unittest.main()
