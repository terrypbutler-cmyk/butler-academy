import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from modules.seating_plan_store import (
    build_printable_plan_html,
    delete_persisted_plan,
    load_persisted_plan,
    plan_export_json,
    save_persisted_plan,
)
from modules.seating_plan_utils import LAYOUT_GROUPS


class SeatingPlanStoreTests(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "layout": LAYOUT_GROUPS,
            "seats": {
                "seat_0": "Alex <script>alert(1)</script>",
                "seat_1": "Sam B.",
            },
            "circulation_path": ["Alex <script>alert(1)</script>"],
            "zones": {"front_edge": "Top"},
            "rationale": {"layout_reason": "Support <strong>talk</strong>."},
            "source": "Unit test",
        }
        self.students = pd.DataFrame(
            {
                "Full Name": ["Alex <script>alert(1)</script>", "Sam B."],
                "SEN Status": ["No", "No"],
                "EAL": ["No", "No"],
                "Disadvantaged (PP)": ["No", "No"],
            }
        )

    def test_save_load_and_delete_one_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            store_path = str(Path(directory) / "plans.json")

            self.assertTrue(save_persisted_plan(store_path, "class-key", self.plan))
            self.assertEqual(
                load_persisted_plan(store_path, "class-key")["seats"],
                self.plan["seats"],
            )
            self.assertTrue(delete_persisted_plan(store_path, "class-key"))
            self.assertIsNone(load_persisted_plan(store_path, "class-key"))

    def test_exports_escape_html_and_limit_json_to_plan_data(self):
        html = build_printable_plan_html(self.plan, self.students, "Year 7")
        payload = json.loads(plan_export_json(self.plan, "Year 7"))

        self.assertIn("Alex &lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("Alex <script>alert(1)</script>", html)
        self.assertIn("Support &lt;strong&gt;talk&lt;/strong&gt;.", html)
        self.assertNotIn("SEN Status", payload)
        self.assertEqual(payload["cohort"], "Year 7")


if __name__ == "__main__":
    unittest.main()
