import unittest

import pandas as pd

from modules.seating_plan_utils import (
    LAYOUT_GROUPS,
    LAYOUT_HORSESHOE,
    LAYOUT_ROWS,
    class_seating_key,
    ensure_suggested_plan,
    find_pupil_seat,
    mentor_evidence_summary,
    order_dataframe_by_plan,
    place_or_swap_pupil,
    rationale_summary_lines,
    seat_zone_labels,
    seating_discussion_groups,
    seating_group_explanations,
    seating_plan_checks,
    suggested_seat_map,
    swap_seated_pupils,
    unseated_pupil_names,
)


class SeatingPlanTests(unittest.TestCase):
    def setUp(self):
        self.students = pd.DataFrame(
            [
                {
                    "Full Name": "Alex A.",
                    "Preferred Peers": "Sam B.; Lee D.",
                    "Pairing Considerations": "Lee D.",
                    "Peer Discussion Style": "Quiet listener",
                    "Academic Confidence": 30,
                    "Independence": 35,
                },
                {
                    "Full Name": "Sam B.",
                    "Preferred Peers": "Alex A.",
                    "Pairing Considerations": "",
                    "Peer Discussion Style": "Collaborative",
                    "Academic Confidence": 65,
                    "Independence": 70,
                },
                {
                    "Full Name": "Jordan C.",
                    "Preferred Peers": "",
                    "Pairing Considerations": "",
                    "Peer Discussion Style": "Supportive",
                    "Academic Confidence": 55,
                    "Independence": 60,
                },
                {
                    "Full Name": "Lee D.",
                    "Preferred Peers": "Alex A.",
                    "Pairing Considerations": "",
                    "Peer Discussion Style": "Takes control",
                    "Academic Confidence": 70,
                    "Independence": 75,
                },
                {
                    "Full Name": "Pat E.",
                    "Preferred Peers": "",
                    "Pairing Considerations": "Alex A.",
                    "Peer Discussion Style": "Collaborative",
                    "Academic Confidence": 60,
                    "Independence": 65,
                },
            ]
        )

    def test_class_key_is_stable_when_dataframe_order_changes(self):
        original = class_seating_key("Year 10", self.students)
        reversed_key = class_seating_key(
            "Year 10",
            self.students.iloc[::-1],
        )

        self.assertEqual(original, reversed_key)

    def test_suggestion_uses_relationships_and_seats_each_student_once(self):
        seats = suggested_seat_map(self.students)
        seated_names = list(seats.values())
        alex_table = {
            seats.get(f"seat_{index}")
            for index in range(4)
        }

        self.assertEqual(set(seated_names), set(self.students["Full Name"]))
        self.assertEqual(len(seated_names), len(set(seated_names)))
        self.assertIn("Sam B.", alex_table)
        self.assertNotIn("Lee D.", alex_table)
        self.assertNotIn("Pat E.", alex_table)

    def test_saved_plan_orders_dataframe_by_seat_number(self):
        plan = {
            "seats": {
                "seat_3": "Alex A.",
                "seat_0": "Jordan C.",
            }
        }

        ordered = order_dataframe_by_plan(self.students, plan)

        self.assertEqual(
            ordered["Full Name"].tolist()[:2],
            ["Jordan C.", "Alex A."],
        )

    def test_ensure_plan_reuses_the_saved_class_plan(self):
        plans = {}

        key, first_plan, created = ensure_suggested_plan(
            plans,
            self.students,
            "Year 10",
        )
        second_key, second_plan, created_again = ensure_suggested_plan(
            plans,
            self.students,
            "Year 10",
        )

        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(key, second_key)
        self.assertIs(first_plan, second_plan)
        self.assertIn("zones", first_plan)
        self.assertIn("rationale", first_plan)

    def test_ensure_plan_removes_retired_room_zone_settings(self):
        plans = {}
        key = class_seating_key("Year 10", self.students)
        plans[key] = {
            "layout": LAYOUT_ROWS,
            "seats": {},
            "circulation_path": [],
            "zones": {
                "front_edge": "Bottom",
                "teacher_start": "Left side",
                "door_side": "Right",
                "calm_zone": "Back left",
            },
        }

        _, plan, created = ensure_suggested_plan(
            plans,
            self.students,
            "Year 10",
        )

        self.assertFalse(created)
        self.assertEqual(
            plan["zones"],
            {"front_edge": "Bottom", "teacher_start": "Left side"},
        )

    def test_discussion_groups_follow_saved_adjacent_seats(self):
        plan = {
            "layout": "Groups (8 Tables)",
            "seats": {
                "seat_0": "Alex A.",
                "seat_1": "Sam B.",
                "seat_2": "Jordan C.",
                "seat_3": "Lee D.",
            },
        }

        pairs = seating_discussion_groups(plan, self.students, group_size=2)
        tables = seating_discussion_groups(plan, self.students, group_size=4)

        self.assertEqual(
            [pair["students"] for pair in pairs],
            [["Alex A.", "Sam B."], ["Jordan C.", "Lee D."]],
        )
        self.assertEqual(
            tables[0]["students"],
            ["Alex A.", "Sam B.", "Jordan C.", "Lee D."],
        )

    def test_place_or_swap_moves_both_seated_pupils(self):
        plan = {
            "seats": {"seat_0": "Alex A.", "seat_1": "Sam B."},
            "circulation_path": ["Alex A.", "Sam B."],
        }

        result = place_or_swap_pupil(plan, "Alex A.", "seat_1")

        self.assertTrue(result["changed"])
        self.assertEqual(result["action"], "swapped")
        self.assertEqual(plan["seats"]["seat_0"], "Sam B.")
        self.assertEqual(plan["seats"]["seat_1"], "Alex A.")

    def test_explicit_swap_and_unseated_bank(self):
        plan = {
            "seats": {"seat_0": "Alex A.", "seat_1": "Sam B."},
            "circulation_path": [],
        }

        self.assertTrue(swap_seated_pupils(plan, "Alex A.", "Sam B."))
        self.assertEqual(find_pupil_seat(plan, "Alex A."), "seat_1")
        self.assertEqual(
            unseated_pupil_names(plan, self.students),
            ["Jordan C.", "Lee D.", "Pat E."],
        )

    def test_group_explanation_uses_reciprocal_preferences(self):
        plan = {
            "layout": LAYOUT_GROUPS,
            "seats": {"seat_0": "Alex A.", "seat_1": "Sam B."},
        }

        explanations = seating_group_explanations(plan, self.students)

        self.assertEqual(len(explanations), 1)
        self.assertTrue(
            any("reciprocal" in reason for reason in explanations[0]["reasons"])
        )

    def test_checks_find_pairing_conflict_and_route_omission(self):
        students = self.students.copy()
        students["SEN Status"] = ["SEND Support", "No", "No", "No", "No"]
        plan = {
            "layout": LAYOUT_GROUPS,
            "seats": {
                "seat_0": "Alex A.",
                "seat_1": "Lee D.",
                "seat_4": "Sam B.",
            },
            "circulation_path": ["Sam B."],
            "zones": {},
        }

        checks = seating_plan_checks(plan, students)

        self.assertEqual(checks["metrics"]["pairing_conflicts"], 1)
        self.assertEqual(checks["priority_route_omissions"], ["Alex A."])

    def test_zone_labels_follow_configured_front_edge(self):
        top_plan = {
            "layout": LAYOUT_ROWS,
            "zones": {"front_edge": "Top"},
        }
        bottom_plan = {
            "layout": LAYOUT_ROWS,
            "zones": {"front_edge": "Bottom"},
        }

        self.assertIn("front", seat_zone_labels(top_plan, "seat_0"))
        self.assertIn("back", seat_zone_labels(bottom_plan, "seat_0"))
        self.assertIn(
            "front",
            seat_zone_labels(
                {"layout": LAYOUT_HORSESHOE, "zones": {"front_edge": "Top"}},
                "seat_0",
            ),
        )

    def test_mentor_summary_includes_rationale_without_full_profiles(self):
        plan = {
            "layout": LAYOUT_GROUPS,
            "seats": {"seat_0": "Alex A.", "seat_1": "Sam B."},
            "circulation_path": [],
            "rationale": {
                "layout_reason": "Protect structured talk.",
                "monitor": "Check Alex A. after modelling.",
            },
        }

        summary = mentor_evidence_summary(plan, self.students)

        self.assertIn("reciprocal match", summary)
        self.assertIn("Why this layout: Protect structured talk.", summary)
        self.assertNotIn("Academic Confidence", summary)
        self.assertNotIn("Alex A.", summary)
        self.assertIn("Check [Pupil 1] after modelling.", summary)
        self.assertEqual(
            rationale_summary_lines(plan),
            [
                "Why this layout: Protect structured talk.",
                "What to monitor: Check Alex A. after modelling.",
            ],
        )


if __name__ == "__main__":
    unittest.main()
