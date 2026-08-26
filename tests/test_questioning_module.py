import unittest

from modules.questioning_module import SCENARIOS, filtered_scenarios, question_ladder


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


if __name__ == "__main__":
    unittest.main()
