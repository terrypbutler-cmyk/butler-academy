import sys
import types
import unittest
from unittest.mock import patch

from modules.reaction_engine import (
    MODIFIER_LABELS,
    NATURAL_LEVEL,
    REACTION_FOCUS_KEY,
    REACTION_INTENSITY_KEY,
    REACTION_OPTIONS_VERSION,
    REACTION_OPTIONS_VERSION_KEY,
    REACTION_SETTING_KEYS,
    REACTION_WIDGET_KEYS,
    ReactionSettings,
    active_reaction_summary,
    apply_interaction_modifier,
    initialise_reaction_settings,
    reaction_settings_from_state,
)
from modules.simulation_options import _save_widget_value


class ReactionOptionTests(unittest.TestCase):
    def test_initialise_sets_natural_defaults_without_overwriting(self):
        confidence_key = REACTION_SETTING_KEYS["confidence"]
        state = {
            confidence_key: 1,
            REACTION_OPTIONS_VERSION_KEY: REACTION_OPTIONS_VERSION,
        }

        initialise_reaction_settings(state)

        self.assertEqual(state[confidence_key], 1)
        self.assertTrue(all(key in state for key in REACTION_SETTING_KEYS.values()))
        self.assertEqual(state[REACTION_FOCUS_KEY], "natural")
        self.assertEqual(state[REACTION_INTENSITY_KEY], "subtle")

    def test_state_upgrade_centres_every_control(self):
        participation_key = REACTION_SETTING_KEYS["participation"]
        state = {
            participation_key: -2,
            REACTION_FOCUS_KEY: "task_refusal",
            REACTION_OPTIONS_VERSION_KEY: REACTION_OPTIONS_VERSION - 1,
        }

        initialise_reaction_settings(state)

        self.assertTrue(
            all(state[key] == NATURAL_LEVEL for key in REACTION_SETTING_KEYS.values())
        )
        self.assertEqual(state[REACTION_FOCUS_KEY], "natural")
        self.assertEqual(state[REACTION_OPTIONS_VERSION_KEY], REACTION_OPTIONS_VERSION)

    def test_modifier_biases_a_temporary_value_without_mutating_source(self):
        source = {"Academic Confidence": 60}

        reduced = apply_interaction_modifier(source["Academic Confidence"], -2)
        increased = apply_interaction_modifier(source["Academic Confidence"], 2)

        self.assertEqual(source["Academic Confidence"], 60)
        self.assertLess(reduced, 60)
        self.assertGreater(increased, 60)
        self.assertLessEqual(increased, 100)

    def test_invalid_state_is_safely_normalised(self):
        state = {
            REACTION_SETTING_KEYS["participation"]: 9,
            REACTION_SETTING_KEYS["confidence"]: "not-a-number",
            REACTION_FOCUS_KEY: "invented",
            REACTION_INTENSITY_KEY: "extreme",
        }

        settings = reaction_settings_from_state(state)

        self.assertEqual(settings.participation, 2)
        self.assertEqual(settings.confidence, NATURAL_LEVEL)
        self.assertEqual(settings.focus, "natural")
        self.assertEqual(settings.intensity, "subtle")

    def test_widget_callback_survives_page_widget_cleanup(self):
        saved_key = REACTION_SETTING_KEYS["participation"]
        widget_key = REACTION_WIDGET_KEYS["participation"]
        state = {saved_key: NATURAL_LEVEL, widget_key: 2}
        fake_streamlit = types.ModuleType("streamlit")
        fake_streamlit.session_state = state

        with patch.dict(sys.modules, {"streamlit": fake_streamlit}):
            _save_widget_value(widget_key, saved_key)
        del state[widget_key]

        self.assertEqual(reaction_settings_from_state(state).participation, 2)

    def test_active_summary_reports_only_non_natural_controls(self):
        settings = ReactionSettings(
            participation=-1,
            answer_security=2,
            focus="passive_non_start",
            intensity="clear",
        )

        self.assertEqual(
            active_reaction_summary(settings),
            [
                f"Participation: {MODIFIER_LABELS[-1]}",
                f"Answer Security: {MODIFIER_LABELS[2]}",
                "Focus: Agrees outwardly but does not begin",
                "Visibility: Clear",
            ],
        )


if __name__ == "__main__":
    unittest.main()
