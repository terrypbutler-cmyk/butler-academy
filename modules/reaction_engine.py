"""Shared, profile-grounded pupil reaction generation for rehearsal tools.

The engine predicts pupil-visible reactions to a teacher stimulus. It deliberately
does not score, coach or judge the teacher. Spreadsheet rows are treated as immutable;
temporary settings influence only the generated interaction.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from collections.abc import Mapping, MutableMapping, Sequence

from config import REACTION_MODEL
from modules import ai_client as genai
from modules.data_utils import get_ai_response_profile


NATURAL_LEVEL = 0
MODIFIER_LEVELS = (-2, -1, 0, 1, 2)
MODIFIER_LABELS = {
    -2: "Much less",
    -1: "Less",
    0: "Natural",
    1: "More",
    2: "Much more",
}

REACTION_SETTING_KEYS = {
    "participation": "saved_reaction_participation",
    "confidence": "saved_reaction_confidence",
    "processing": "saved_reaction_processing",
    "independence": "saved_reaction_independence",
    "answer_security": "saved_reaction_answer_security",
}
REACTION_WIDGET_KEYS = {
    name: f"reaction_slider_{name}"
    for name in REACTION_SETTING_KEYS
}
REACTION_FOCUS_KEY = "saved_reaction_focus"
REACTION_FOCUS_WIDGET_KEY = "reaction_focus_widget"
REACTION_INTENSITY_KEY = "saved_reaction_intensity"
REACTION_INTENSITY_WIDGET_KEY = "reaction_intensity_widget"
REACTION_OPTIONS_VERSION_KEY = "_reaction_options_version"
REACTION_OPTIONS_VERSION = 1

REACTION_FOCUS_LABELS = {
    "natural": "Natural profile",
    "quiet_non_participation": "Quiet non-participation",
    "idk_withdrawal": "‘I don’t know’ followed by withdrawal",
    "public_challenge": "Public challenge to an instruction",
    "task_refusal": "Task refusal",
    "confident_misconception": "Confident misconception",
    "peer_distraction": "Peer distraction during discussion",
    "passive_non_start": "Agrees outwardly but does not begin",
}
REACTION_TYPES = {
    "ordinary_engagement",
    *[key for key in REACTION_FOCUS_LABELS if key != "natural"],
}
PARTICIPATION_STATES = {
    "engaged",
    "hesitant",
    "quiet",
    "withdrawn",
    "questioning",
    "refusing",
    "distracted",
    "passively_compliant",
}
ACADEMIC_STATES = {
    "not_assessed",
    "secure",
    "partial",
    "misconception",
    "uncertain",
    "no_attempt",
}
ALLOWED_AFFECT = {
    "neutral",
    "hesitant",
    "frustrated",
    "defensive",
    "bored",
    "interested",
    "eager",
}


@dataclass(frozen=True)
class ReactionSettings:
    """Temporary interaction emphasis; zero means use the original profile."""

    participation: int = 0
    confidence: int = 0
    processing: int = 0
    independence: int = 0
    answer_security: int = 0
    focus: str = "natural"
    intensity: str = "subtle"


@dataclass(frozen=True)
class ReactionState:
    """Small pupil state carried between teacher stimuli."""

    participation: str = "engaged"
    academic: str = "not_assessed"
    affect: str = "neutral"
    began_task: bool | None = None
    turn: int = 0


@dataclass(frozen=True)
class ReactionResult:
    """Structured pupil reaction returned to every interactive tool."""

    reaction_type: str
    dialogue: str
    visible_behaviour: str
    participation_state: str
    academic_state: str
    affect: str
    began_task: bool | None
    state_summary: str
    hypothetical_example: bool = False

    def next_state(self, prior: ReactionState | None = None) -> ReactionState:
        previous = prior or ReactionState()
        return ReactionState(
            participation=self.participation_state,
            academic=self.academic_state,
            affect=self.affect,
            began_task=self.began_task,
            turn=previous.turn + 1,
        )

    def display_text(self) -> str:
        action = self.visible_behaviour.strip().strip("*")
        dialogue = self.dialogue.strip()
        if action and dialogue:
            return f"*{action}* {dialogue}"
        if action:
            return f"*{action}*"
        return dialogue or "…"


def initialise_reaction_settings(state: MutableMapping) -> None:
    """Initialise persistent settings without attaching them to page widgets."""
    if state.get(REACTION_OPTIONS_VERSION_KEY) != REACTION_OPTIONS_VERSION:
        for key in REACTION_SETTING_KEYS.values():
            state[key] = NATURAL_LEVEL
        state[REACTION_FOCUS_KEY] = "natural"
        state[REACTION_INTENSITY_KEY] = "subtle"
        state[REACTION_OPTIONS_VERSION_KEY] = REACTION_OPTIONS_VERSION
        return

    for key in REACTION_SETTING_KEYS.values():
        state.setdefault(key, NATURAL_LEVEL)
    state.setdefault(REACTION_FOCUS_KEY, "natural")
    state.setdefault(REACTION_INTENSITY_KEY, "subtle")


def _bounded_level(value) -> int:
    try:
        level = int(value)
    except (TypeError, ValueError):
        level = NATURAL_LEVEL
    return min(max(level, min(MODIFIER_LEVELS)), max(MODIFIER_LEVELS))


def reaction_settings_from_state(state: Mapping) -> ReactionSettings:
    """Read a safe settings object from Streamlit-like session state."""
    values = {
        name: _bounded_level(state.get(key, NATURAL_LEVEL))
        for name, key in REACTION_SETTING_KEYS.items()
    }
    focus = str(state.get(REACTION_FOCUS_KEY, "natural"))
    if focus not in REACTION_FOCUS_LABELS:
        focus = "natural"
    intensity = str(state.get(REACTION_INTENSITY_KEY, "subtle"))
    if intensity not in {"subtle", "clear"}:
        intensity = "subtle"
    return ReactionSettings(**values, focus=focus, intensity=intensity)


def active_reaction_summary(settings: ReactionSettings) -> list[str]:
    """Return concise descriptions of non-natural scenario controls."""
    summary = []
    for name in REACTION_SETTING_KEYS:
        level = getattr(settings, name)
        if level:
            label = name.replace("_", " ").title()
            summary.append(f"{label}: {MODIFIER_LABELS[level]}")
    if settings.focus != "natural":
        summary.append(f"Focus: {REACTION_FOCUS_LABELS[settings.focus]}")
        summary.append(f"Visibility: {settings.intensity.title()}")
    return summary


def apply_interaction_modifier(value, level: int) -> float:
    """Bias a 0–100 value without changing its source dataframe value."""
    try:
        base = max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        base = 50.0
    level = _bounded_level(level)
    strength = {0: 0.0, 1: 0.20, 2: 0.40}.get(abs(level), 0.0)
    if level > 0:
        return base + (100.0 - base) * strength
    if level < 0:
        return base * (1.0 - strength)
    return base


def _clean_value(value) -> str:
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    if text.casefold() in {"", "nan", "none", "null", "n/a", "0", "false"}:
        return ""
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _row_value(row, columns: Sequence[str]) -> str:
    available = {str(column).strip().casefold(): column for column in row.keys()}
    for candidate in columns:
        column = available.get(candidate.strip().casefold())
        if column is None:
            continue
        value = _clean_value(row[column])
        if value:
            return value
    return ""


def _numeric(row, columns: Sequence[str], default=50.0) -> float:
    text = _row_value(row, columns)
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return float(default)
    try:
        return max(0.0, min(100.0, float(match.group(0))))
    except ValueError:
        return float(default)


def _interaction_text(row) -> str:
    fields = (
        "Cold Call Response",
        "Cold-call response",
        "Peer Discussion Style",
        "Typical Learning Barrier",
        "Learning Barrier",
        "Current Learning Target",
        "Helpful Scaffold",
        "Pairing Considerations",
    )
    return " | ".join(_row_value(row, [field]) for field in fields).casefold()


def focus_support(row, focus: str) -> tuple[bool, list[str]]:
    """Check whether a named-pupil focus has direct, non-demographic support."""
    if focus == "natural":
        return True, []

    text = _interaction_text(row)
    participation = _numeric(row, ["Participation Level"])
    confidence = _numeric(row, ["Academic Confidence"])
    processing = _numeric(row, ["Processing Speed"])
    independence = _numeric(row, ["Independence"])
    evidence = []

    keyword_sets = {
        "quiet_non_participation": ("quiet", "reluctant", "hesitant", "waits to be asked", "listener"),
        "idk_withdrawal": ("i don't know", "not sure", "withdraw", "reluctant", "hesitant"),
        "public_challenge": ("challenges", "questions instruction", "argues", "confront", "defiant"),
        "task_refusal": ("refus", "won't", "will not", "task avoidance", "avoidance"),
        "peer_distraction": ("distract", "off task", "off-task", "chatty", "side conversation"),
        "passive_non_start": ("needs prompting", "does not start", "delayed start", "reassurance", "waits for adult"),
    }
    for keyword in keyword_sets.get(focus, ()): 
        if keyword in text:
            evidence.append(f"recorded interaction signal: {keyword}")
            break

    if focus == "quiet_non_participation" and participation <= 40:
        evidence.append(f"participation {participation:.0f}/100")
    elif focus == "idk_withdrawal" and confidence <= 40:
        evidence.append(f"confidence {confidence:.0f}/100")
    elif focus == "confident_misconception" and confidence >= 60:
        evidence.append(f"confidence {confidence:.0f}/100")
    elif focus == "passive_non_start":
        if independence <= 45:
            evidence.append(f"independence {independence:.0f}/100")
        if processing <= 45:
            evidence.append(f"processing speed {processing:.0f}/100")

    # Strong behavioural reactions need explicit recorded evidence. Academic and
    # low-participation examples may also be supported by relevant numeric evidence.
    if focus in {"public_challenge", "task_refusal", "peer_distraction"}:
        return bool(evidence and evidence[0].startswith("recorded")), evidence
    return bool(evidence), evidence


def reaction_instruction_block(
    settings: ReactionSettings,
    *,
    focus_supported: bool = True,
    context: str = "classroom interaction",
) -> str:
    """Create shared reaction rules for individual and batch AI prompts."""
    trait_rules = {
        "participation": "willingness and visibility of contribution",
        "confidence": "certainty, tentativeness and readiness to risk an answer",
        "processing": "pause length, response latency and speed of beginning",
        "independence": "need for prompting, reassurance or a clarified first step",
        "answer_security": "likelihood of secure, partial, uncertain or mistaken academic content",
    }
    active_traits = []
    for name, description in trait_rules.items():
        level = getattr(settings, name)
        if level:
            active_traits.append(
                f"- {name.replace('_', ' ').title()}: {MODIFIER_LABELS[level]}. "
                f"Temporarily bias {description}; do not claim the stored profile changed."
            )
    trait_text = "\n".join(active_traits) or "- All traits remain at their natural recorded profile level."

    if settings.focus == "natural":
        focus_text = (
            "Use the most plausible ordinary reaction. Do not force resistance; a normal, "
            "engaged or partially successful response is often the best prediction."
        )
    else:
        label = REACTION_FOCUS_LABELS[settings.focus]
        support_note = (
            "This focus has direct profile support."
            if focus_supported
            else "This is a teacher-selected HYPOTHETICAL teaching example, not a profile prediction."
        )
        focus_text = (
            f"Teaching-example focus: {label}. {support_note} Render it at "
            f"{settings.intensity.upper()} visibility, remaining mild and age-authentic."
        )

    return f"""
SHARED PUPIL REACTION ENGINE — {context}
Predict only the pupil's reaction to the supplied stimulus. Do not score, grade,
coach, praise or criticise the teacher and do not recommend a better teacher move.

Temporary interaction emphasis:
{trait_text}

{focus_text}

Reaction safeguards:
- Keep behaviour mild and stateful. Begin with a subtle cue; never jump to shouting,
  aggression, abuse or crisis behaviour.
- Separate participation from academic accuracy. Low attainment does not imply poor
  behaviour; slow processing does not imply refusal; quietness does not imply challenge.
- Specific SEND detail may shape access, sensory load, processing or communication only
  when directly relevant. EAL may shape vocabulary, latency and response length, not
  intelligence. PP and ethnicity must not be used to infer refusal, distraction,
  compliance, challenge, motivation or attainment.
- Never mention profile fields, modifiers, SEND, EAL, PP, ethnicity or scores in the
  pupil's words. Never invent home-life or safeguarding information.
- A teacher stimulus may lead to repair, maintenance or one mild step of escalation, but
  do not decide whether the teacher was good or bad. Show the consequence only through
  what the pupil says and visibly does.
""".strip()


def _state_dict(state: ReactionState | Mapping | None) -> dict:
    if state is None:
        return asdict(ReactionState())
    if isinstance(state, ReactionState):
        return asdict(state)
    return {
        "participation": str(state.get("participation", "engaged")),
        "academic": str(state.get("academic", "not_assessed")),
        "affect": str(state.get("affect", "neutral")),
        "began_task": state.get("began_task"),
        "turn": int(state.get("turn", 0)),
    }


def build_reaction_prompt(
    row,
    cohort: str,
    teacher_stimulus: str,
    classroom_context: str,
    settings: ReactionSettings,
    *,
    subject: str = "",
    history: Sequence[Mapping] = (),
    state: ReactionState | Mapping | None = None,
) -> tuple[str, bool, list[str]]:
    """Build the structured prompt and disclose whether focus is hypothetical."""
    supported, evidence = focus_support(row, settings.focus)
    name = _row_value(row, ["Full Name", "Preferred Name"]) or "Student"
    profile = get_ai_response_profile(row, cohort, subject)
    state_data = _state_dict(state)
    recent_history = list(history)[-8:]
    engine_rules = reaction_instruction_block(
        settings,
        focus_supported=supported,
        context=classroom_context,
    )
    prompt = f"""
You are predicting the next visible reaction of {name}, a {cohort} pupil, for a
teacher-controlled classroom rehearsal. This is a plausible prediction, not an observed
fact or a judgement about the real pupil.

Compact approved response profile:
{profile}

Subject: {subject or 'Not specified'}
Classroom context: {classroom_context}
Current pupil state: {json.dumps(state_data, ensure_ascii=False)}
Recent interaction: {json.dumps(recent_history, ensure_ascii=False)}
Teacher stimulus: {teacher_stimulus}

{engine_rules}

Return only JSON with exactly these keys:
{{
  "reaction_type": "ordinary_engagement | quiet_non_participation | idk_withdrawal | public_challenge | task_refusal | confident_misconception | peer_distraction | passive_non_start",
  "dialogue": "zero to two short age-authentic spoken sentences",
  "visible_behaviour": "one brief observable action, with no interpretation",
  "participation_state": "engaged | hesitant | quiet | withdrawn | questioning | refusing | distracted | passively_compliant",
  "academic_state": "not_assessed | secure | partial | misconception | uncertain | no_attempt",
  "affect": "neutral | hesitant | frustrated | defensive | bored | interested | eager",
  "began_task": true | false | null,
  "state_summary": "one short factual state description without judging the teacher"
}}
""".strip()
    return prompt, not supported and settings.focus != "natural", evidence


def _choice(value, allowed: set[str], fallback: str) -> str:
    clean = str(value or "").strip().casefold().replace(" ", "_")
    return clean if clean in allowed else fallback


def normalise_reaction_result(payload, *, hypothetical=False) -> ReactionResult:
    """Constrain model output to the shared mild reaction contract."""
    data = payload if isinstance(payload, Mapping) else {}
    dialogue = str(data.get("dialogue", "")).strip()[:360]
    visible = str(data.get("visible_behaviour", "")).strip().strip("*")[:220]
    began_task = data.get("began_task")
    if began_task not in {True, False, None}:
        began_task = None
    return ReactionResult(
        reaction_type=_choice(
            data.get("reaction_type"),
            REACTION_TYPES,
            "ordinary_engagement",
        ),
        dialogue=dialogue,
        visible_behaviour=visible,
        participation_state=_choice(
            data.get("participation_state"),
            PARTICIPATION_STATES,
            "engaged",
        ),
        academic_state=_choice(
            data.get("academic_state"),
            ACADEMIC_STATES,
            "not_assessed",
        ),
        affect=_choice(data.get("affect"), ALLOWED_AFFECT, "neutral"),
        began_task=began_task,
        state_summary=str(data.get("state_summary", "")).strip()[:280],
        hypothetical_example=bool(hypothetical),
    )


def reaction_cache_key(
    row,
    teacher_stimulus: str,
    classroom_context: str,
    settings: ReactionSettings,
    state: ReactionState | Mapping | None,
    history: Sequence[Mapping] = (),
) -> str:
    """Create a stable key so exact replay returns the exact recorded reaction."""
    payload = {
        "name": _row_value(row, ["Full Name", "Preferred Name"]),
        "stimulus": teacher_stimulus.strip(),
        "context": classroom_context.strip(),
        "settings": asdict(settings),
        "state": _state_dict(state),
        "history": list(history)[-8:],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def generate_reaction(
    row,
    cohort: str,
    teacher_stimulus: str,
    classroom_context: str,
    settings: ReactionSettings,
    *,
    subject: str = "",
    history: Sequence[Mapping] = (),
    state: ReactionState | Mapping | None = None,
    cache: MutableMapping | None = None,
) -> tuple[ReactionResult, list[str]]:
    """Generate or replay one pupil reaction using the selected AI provider."""
    cache_key = reaction_cache_key(
        row,
        teacher_stimulus,
        classroom_context,
        settings,
        state,
        history,
    )
    if cache is not None and cache_key in cache:
        cached = cache[cache_key]
        return normalise_reaction_result(
            cached.get("result", cached),
            hypothetical=bool(cached.get("hypothetical", False)),
        ), list(cached.get("evidence", []))

    prompt, hypothetical, evidence = build_reaction_prompt(
        row,
        cohort,
        teacher_stimulus,
        classroom_context,
        settings,
        subject=subject,
        history=history,
        state=state,
    )
    model = genai.GenerativeModel(REACTION_MODEL)
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
    )
    raw_text = response.text.replace("```json", "").replace("```", "")
    payload = json.loads(raw_text.strip())
    result = normalise_reaction_result(payload, hypothetical=hypothetical)
    if cache is not None:
        cache[cache_key] = {
            "result": asdict(result),
            "hypothetical": hypothetical,
            "evidence": evidence,
        }
    return result, evidence
