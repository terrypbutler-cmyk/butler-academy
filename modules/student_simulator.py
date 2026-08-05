"""Interactive, stateful pupil reaction simulator."""

from dataclasses import asdict
import hashlib
import json
import re

import streamlit as st

from modules import ai_client as genai
from modules.app_shell import (
    get_teacher_address_options,
    get_teacher_display_name,
)
from modules.photo_utils import display_student_photo
from modules.reaction_engine import (
    REACTION_FOCUS_LABELS,
    ReactionState,
    active_reaction_summary,
    focus_support,
    generate_reaction,
    reaction_settings_from_state,
)

try:
    from modules.academic_responses import (
        get_elevenlabs_audio,
        get_student_voice_id,
    )
except ImportError:
    get_elevenlabs_audio = None
    get_student_voice_id = None


CONTEXTS = (
    "Academic question or probe",
    "Independent task instruction",
    "Public instruction or correction",
    "Private check-in",
    "End-of-lesson interaction",
    "Corridor interaction",
    "Peer discussion",
)


def _value(row, possible_names, default="None recorded"):
    row_keys = {str(key).strip().casefold(): key for key in row.keys()}
    for name in possible_names:
        key = row_keys.get(name.strip().casefold())
        if key is None:
            continue
        value = str(row[key]).strip()
        if value and value.casefold() not in {"nan", "n/a", "none", "null"}:
            return value[:-2] if value.endswith(".0") else value
    return default


def _scenario_keys(student, teacher_key, context, settings):
    signature = hashlib.sha1(
        json.dumps(
            {
                "student": student,
                "teacher": teacher_key,
                "context": context,
                "settings": asdict(settings),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:14]
    return {
        "messages": f"reaction_messages_{signature}",
        "state": f"reaction_state_{signature}",
        "cache": f"reaction_cache_{signature}",
        "replay": f"reaction_replay_{signature}",
        "last_trace": f"reaction_last_trace_{signature}",
    }


def _reset_trace(keys, *, keep_cache):
    if keep_cache:
        st.session_state[keys["last_trace"]] = list(
            st.session_state.get(keys["messages"], [])
        )
    st.session_state[keys["messages"]] = []
    st.session_state[keys["state"]] = asdict(ReactionState())
    st.session_state[keys["replay"]] = bool(keep_cache)
    if not keep_cache:
        st.session_state[keys["cache"]] = {}


def render_simulator(df, cohort):
    teacher_name = get_teacher_display_name()
    teacher_addresses = get_teacher_address_options(teacher_name)
    settings = reaction_settings_from_state(st.session_state)

    header, voice_column = st.columns([3, 1])
    with header:
        st.subheader("🤖 Stateful pupil reaction simulator")
        st.caption(
            "Enter a teacher stimulus and observe a profile-informed pupil reaction. "
            "The app predicts the pupil only; it does not score or judge the teacher."
        )
    with voice_column:
        enable_voice = st.toggle(
            "🔊 Voice audio",
            value=True,
            key="sim_voice_toggle",
        )

    if not genai.configure_selected_provider():
        return

    pupil_names = df["Full Name"].astype(str).tolist()
    selected_student = st.selectbox("Select pupil", pupil_names)
    context = st.selectbox("Classroom context", CONTEXTS)
    if not selected_student:
        return

    row = df[df["Full Name"].astype(str) == selected_student].iloc[0]
    teacher_key = re.sub(
        r"[^a-z0-9]+",
        "_",
        "|".join(teacher_addresses).casefold(),
    ).strip("_") or "teacher"
    keys = _scenario_keys(selected_student, teacher_key, context, settings)
    st.session_state.setdefault(keys["messages"], [])
    st.session_state.setdefault(keys["state"], asdict(ReactionState()))
    st.session_state.setdefault(keys["cache"], {})
    st.session_state.setdefault(keys["replay"], False)
    st.session_state.setdefault(keys["last_trace"], [])

    active = active_reaction_summary(settings)
    if active:
        st.info("Scenario controls: " + " · ".join(active))

    supported, evidence = focus_support(row, settings.focus)
    if settings.focus != "natural" and not supported:
        st.warning(
            f"{REACTION_FOCUS_LABELS[settings.focus]} is not strongly supported by "
            "the recorded interaction profile. It will be clearly treated as a "
            "hypothetical teaching example."
        )
    elif settings.focus != "natural" and evidence:
        st.caption("Profile support: " + " · ".join(evidence))

    profile_column, interaction_column = st.columns([1, 2])
    with profile_column:
        with st.container(border=True):
            display_student_photo(selected_student, cohort)
            st.markdown(f"**{selected_student} · {cohort}**")
            st.caption(f"SEND: {_value(row, ['SEN Status', 'SEND Status'])}")
            st.caption(f"EAL: {_value(row, ['EAL', 'EAL Status'])}")
            st.caption(
                "Predicted grade: "
                + _value(row, ["Projected Grade", "Predicted Grade"])
            )
            st.caption(
                "Interaction pattern: "
                + _value(
                    row,
                    ["Cold Call Response", "Peer Discussion Style"],
                )
            )

        replay_column, new_column = st.columns(2)
        with replay_column:
            if st.button(
                "↻ Replay scenario",
                width="stretch",
                disabled=not st.session_state[keys["messages"]],
                help=(
                    "Return to the same starting state and retain exact cached "
                    "reactions for repeated teacher stimuli."
                ),
            ):
                _reset_trace(keys, keep_cache=True)
                st.rerun()
        with new_column:
            if st.button(
                "✦ New variation",
                width="stretch",
                help="Clear the interaction and allow fresh plausible wording.",
            ):
                _reset_trace(keys, keep_cache=False)
                st.rerun()

        if st.session_state[keys["replay"]]:
            st.success(
                "Replay ready: same pupil, context, controls and starting state."
            )
            previous_trace = st.session_state[keys["last_trace"]]
            if previous_trace:
                with st.expander("Previous interaction to replay", expanded=False):
                    for message in previous_trace:
                        speaker = (
                            teacher_name
                            if message["role"] == "user"
                            else selected_student
                        )
                        st.markdown(f"**{speaker}:** {message['content']}")

    with interaction_column:
        audio_key = f"latest_audio_{keys['messages']}"
        if audio_key in st.session_state:
            st.audio(
                st.session_state.pop(audio_key),
                format="audio/wav",
                autoplay=True,
            )

        messages = st.session_state[keys["messages"]]
        for message in messages:
            with st.chat_message(message["role"]):
                speaker = teacher_name if message["role"] == "user" else selected_student
                st.markdown(f"**{speaker}**")
                st.write(message["content"])
                if message["role"] == "assistant" and message.get("reaction_type"):
                    label = REACTION_FOCUS_LABELS.get(
                        message["reaction_type"],
                        "Ordinary engagement",
                    )
                    suffix = " · hypothetical example" if message.get("hypothetical") else ""
                    st.caption(f"Predicted reaction: {label}{suffix}")

        teacher_input = st.chat_input(
            f"Provide the next teacher stimulus to {selected_student}…"
        )
        if not teacher_input:
            return

        st.session_state[keys["replay"]] = False
        messages.append({"role": "user", "content": teacher_input})
        with st.chat_message("user"):
            st.markdown(f"**{teacher_name}**")
            st.write(teacher_input)

        history = [
            {
                "speaker": teacher_name if item["role"] == "user" else selected_student,
                "text": item["content"],
            }
            for item in messages[:-1]
        ]
        with st.spinner(f"Predicting {selected_student}'s reaction…"):
            try:
                prior_state = ReactionState(**st.session_state[keys["state"]])
                result, _ = generate_reaction(
                    row,
                    cohort,
                    teacher_input,
                    context,
                    settings,
                    history=history,
                    state=prior_state,
                    cache=st.session_state[keys["cache"]],
                )
            except Exception as exc:
                st.error(f"{genai.provider_name()} reaction error: {exc}")
                return

        display_text = result.display_text()
        messages.append(
            {
                "role": "assistant",
                "content": display_text,
                "reaction_type": result.reaction_type,
                "hypothetical": result.hypothetical_example,
                "state_summary": result.state_summary,
            }
        )
        st.session_state[keys["state"]] = asdict(result.next_state(prior_state))

        with st.chat_message("assistant"):
            st.markdown(f"**{selected_student}**")
            st.write(display_text)
            label = REACTION_FOCUS_LABELS.get(
                result.reaction_type,
                "Ordinary engagement",
            )
            suffix = " · hypothetical example" if result.hypothetical_example else ""
            st.caption(f"Predicted reaction: {label}{suffix}")
            if result.state_summary:
                st.caption(result.state_summary)

        st.toast(f"Predicted pupil state: {result.affect.upper()} 🎭")

        audio_text = re.sub(r"[*\[(].*?[*\])]", "", display_text).strip()
        if (
            enable_voice
            and audio_text
            and get_elevenlabs_audio is not None
            and get_student_voice_id is not None
        ):
            try:
                audio_bytes = get_elevenlabs_audio(
                    audio_text,
                    get_student_voice_id(row),
                    cohort,
                )
                if audio_bytes:
                    st.session_state[audio_key] = audio_bytes
                    st.rerun()
            except Exception as exc:
                st.warning(f"Voice audio was unavailable: {exc}")
