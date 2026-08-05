"""Streamlit controls for temporary pupil-interaction scenario emphasis."""

from modules.reaction_engine import (
    MODIFIER_LABELS,
    MODIFIER_LEVELS,
    NATURAL_LEVEL,
    REACTION_FOCUS_KEY,
    REACTION_FOCUS_LABELS,
    REACTION_FOCUS_WIDGET_KEY,
    REACTION_INTENSITY_KEY,
    REACTION_INTENSITY_WIDGET_KEY,
    REACTION_SETTING_KEYS,
    REACTION_WIDGET_KEYS,
    active_reaction_summary,
    initialise_reaction_settings,
    reaction_settings_from_state,
)


TRAIT_LABELS = {
    "participation": "Participation expression",
    "confidence": "Academic confidence",
    "processing": "Processing speed",
    "independence": "Independence",
    "answer_security": "Answer security",
}


def _save_widget_value(widget_key: str, state_key: str) -> None:
    """Copy page-bound widget state into a persistent non-widget key."""
    import streamlit as st

    st.session_state[state_key] = st.session_state[widget_key]


def _reset_reaction_options() -> None:
    """Return both persistent and displayed controls to the natural profile."""
    import streamlit as st

    for name, state_key in REACTION_SETTING_KEYS.items():
        st.session_state[state_key] = NATURAL_LEVEL
        widget_key = REACTION_WIDGET_KEYS[name]
        if widget_key in st.session_state:
            st.session_state[widget_key] = NATURAL_LEVEL
    st.session_state[REACTION_FOCUS_KEY] = "natural"
    st.session_state[REACTION_INTENSITY_KEY] = "subtle"
    if REACTION_FOCUS_WIDGET_KEY in st.session_state:
        st.session_state[REACTION_FOCUS_WIDGET_KEY] = "natural"
    if REACTION_INTENSITY_WIDGET_KEY in st.session_state:
        st.session_state[REACTION_INTENSITY_WIDGET_KEY] = "subtle"


def _render_trait_slider(name: str) -> None:
    import streamlit as st

    state_key = REACTION_SETTING_KEYS[name]
    widget_key = REACTION_WIDGET_KEYS[name]
    kwargs = {}
    if widget_key not in st.session_state:
        kwargs["value"] = reaction_settings_from_state(st.session_state).__dict__[name]
    st.select_slider(
        TRAIT_LABELS[name],
        options=list(MODIFIER_LEVELS),
        format_func=lambda level: MODIFIER_LABELS[level],
        key=widget_key,
        on_change=_save_widget_value,
        args=(widget_key, state_key),
        help=(
            "Temporarily changes how strongly this characteristic is expressed in "
            "generated interactions. It never changes the spreadsheet or pupil record."
        ),
        **kwargs,
    )


def render_reaction_options() -> None:
    """Render centred interaction controls and optional teaching-example focus."""
    import streamlit as st

    st.subheader("Pupil interaction scenario controls")
    st.write(
        "Use the natural profile or temporarily emphasise a characteristic for a "
        "teaching example. These controls influence generated reactions only; pupil "
        "records, analytics, seating evidence and spreadsheet values remain unchanged."
    )

    first_row = st.columns(2)
    second_row = st.columns(2)
    for container, name in zip(
        [*first_row, *second_row],
        ("participation", "confidence", "processing", "independence"),
    ):
        with container:
            _render_trait_slider(name)

    _render_trait_slider("answer_security")
    st.caption(
        "Answer security changes the likelihood of secure, partial, uncertain or "
        "mistaken academic content. It does not change recorded grades."
    )

    st.divider()
    st.markdown("#### Optional teaching-example focus")
    focus_kwargs = {}
    if REACTION_FOCUS_WIDGET_KEY not in st.session_state:
        focus_kwargs["index"] = list(REACTION_FOCUS_LABELS).index(
            reaction_settings_from_state(st.session_state).focus
        )
    focus = st.selectbox(
        "Reaction focus",
        list(REACTION_FOCUS_LABELS),
        format_func=lambda key: REACTION_FOCUS_LABELS[key],
        key=REACTION_FOCUS_WIDGET_KEY,
        on_change=_save_widget_value,
        args=(REACTION_FOCUS_WIDGET_KEY, REACTION_FOCUS_KEY),
        help=(
            "Natural profile lets the engine choose. A selected focus gently biases "
            "the reaction and is labelled hypothetical when the profile does not support it."
        ),
        **focus_kwargs,
    )

    intensity_kwargs = {}
    if REACTION_INTENSITY_WIDGET_KEY not in st.session_state:
        intensity_kwargs["index"] = (
            0
            if reaction_settings_from_state(st.session_state).intensity == "subtle"
            else 1
        )
    st.radio(
        "Visibility",
        ["subtle", "clear"],
        format_func=str.title,
        horizontal=True,
        key=REACTION_INTENSITY_WIDGET_KEY,
        on_change=_save_widget_value,
        args=(REACTION_INTENSITY_WIDGET_KEY, REACTION_INTENSITY_KEY),
        disabled=focus == "natural",
        help="Clear makes the selected teaching example easier to notice, never extreme.",
        **intensity_kwargs,
    )

    reset_col, note_col = st.columns([1, 3])
    with reset_col:
        st.button(
            "Reset to natural profile",
            width="stretch",
            on_click=_reset_reaction_options,
        )
    with note_col:
        st.caption(
            "Controls apply to newly generated interactions in every reaction-enabled "
            "tool. Existing transcripts remain unchanged until replayed or reset."
        )


def render_reaction_option_status() -> None:
    """Show active interaction emphasis in the sidebar."""
    import streamlit as st

    settings = reaction_settings_from_state(st.session_state)
    active = active_reaction_summary(settings)
    if not active:
        st.sidebar.caption("Pupil interactions: natural profile")
        return
    st.sidebar.caption("Interaction scenario controls active:")
    for label in active:
        st.sidebar.caption(f"• {label}")


# Compatibility aliases for older deployments while app.py moves to the clearer names.
initialise_score_options = initialise_reaction_settings
render_score_options = render_reaction_options
render_score_option_status = render_reaction_option_status
