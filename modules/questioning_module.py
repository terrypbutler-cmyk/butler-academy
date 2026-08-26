"""Deliberate-practice page for questioning mathematical misconceptions."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class MisconceptionScenario:
    title: str
    strand: str
    prompt: str
    response: str
    thinking: str
    contrast: str
    accidental: bool = False


def _s(title, strand, prompt, response, thinking, contrast, accidental=False):
    return MisconceptionScenario(title, strand, prompt, response, thinking, contrast, accidental)


SCENARIOS = (
    _s("Mean or median?", "Statistics", "Find the mean of 2, 4 and 6.", "4 — it is the number in the middle.", "Mean is being treated as the physical middle value, not equal sharing.", "Find the mean of 2, 4 and 9, where the middle number and mean differ.", True),
    _s("Percentage increase and decrease", "Proportion", "A £100 item rises by 20%, then falls by 20%. What is its final price?", "£100 — plus 20% and minus 20% cancel.", "Both percentages are assumed to use the same starting quantity.", "Label the whole before each percentage calculation."),
    _s("Squaring a negative", "Number", "Calculate -3².", "9 — a negative times a negative is positive.", "-3² is read as (-3)²; the scope of the exponent is unclear.", "Rewrite and compare -3² and (-3)² as multiplication."),
    _s("Adding fractions", "Fractions", "Calculate 1/2 + 1/3.", "2/5 — add the tops and add the bottoms.", "Numerators and denominators are treated as separate whole-number pairs.", "Use one shared whole and ask whether the result should exceed 1/2."),
    _s("Gradient and intercept", "Algebra", "For y = 2x + 3, identify the gradient and y-intercept.", "The gradient is 3 and the intercept is 2.", "The two remembered values in y = mx + c have been swapped.", "Find y when x = 0, then compare y-values as x increases by 1."),
    _s("Expanding a squared bracket", "Algebra", "Expand (x + 3)².", "x² + 9.", "Square is interpreted as squaring each term separately.", "Rewrite (x + 3)² as a product before expanding."),
    _s("Solving an inequality", "Algebra", "Solve -2x < 6.", "x < -3.", "Inequalities are manipulated exactly like equations; direction is treated as fixed.", "Test x = -4 and x = 0 in the original inequality."),
    _s("Roots of a quadratic", "Algebra", "Solve x² = 16.", "x = 4.", "Square root is assumed to produce only one solution.", "Substitute both 4 and -4 into the original equation."),
    _s("Direct proportion", "Proportion", "Three notebooks cost £6. What do six cost?", "£12 — three more notebooks means another £6.", "A correct answer is supported by additive, not multiplicative, reasoning.", "Ask for nine notebooks or one notebook using the same method.", True),
    _s("Equally likely outcomes", "Probability", "A bag has 2 red and 6 blue counters. What is P(red)?", "1/2 — there are two possible colours.", "Categories are counted instead of equally likely individual outcomes.", "Ask if red and blue stay equally likely after adding 100 blue counters."),
    _s("Multiplying negatives", "Number", "Calculate (-3) × (-4).", "12 — two negatives make a positive.", "A slogan is applied whenever two negative signs appear.", "Compare (-3) × (-4), (-3) + (-4), and 3 - (-4).", True),
    _s("Dividing fractions", "Fractions", "Calculate 2/3 ÷ 4/5.", "2/3 × 4/5.", "The divide sign is changed without using a reciprocal.", "Use 1 ÷ 1/2 and ask what equivalent multiplication gives the result."),
    _s("Ratio as a difference", "Proportion", "Red and blue counters are in the ratio 2:3. There are 6 red. How many blue?", "7 — blue is always one more.", "Ratio is seen as a fixed additive difference.", "Build one, two and three complete batches of the ratio."),
    _s("Equivalent fractions", "Fractions", "Is 2/4 equal to 3/6?", "Yes — add 1 to the top and 2 to the bottom.", "A coincidental additive change is treated as a general equivalence rule.", "Apply the rule to 1/2, or represent both fractions using equal wholes.", True),
    _s("Multiplying decimals", "Number", "Calculate 0.4 × 0.5.", "0.20 — 4 × 5 is 20, then put a decimal point in front.", "A successful placement routine is not linked to magnitude or tenths.", "Predict whether the answer is greater or less than 0.4, then model tenths of tenths.", True),
    _s("Subtracting a negative", "Number", "Calculate 5 - (-3).", "2 — the second negative can be ignored.", "The signs are treated as cancelling without interpreting subtraction.", "Represent the calculation as movement on a number line."),
    _s("Solving equations", "Algebra", "Solve 3x + 5 = 20.", "3x = 20 - 5, so x = 5.", "Terms are imagined to move and change sign rather than equality being maintained.", "Ask what operation was performed on each side of the equation.", True),
    _s("Meaning of equals", "Algebra", "Complete 8 + 4 = □ + 5.", "12.", "Equals is read as ‘the answer comes next’, not as a relationship.", "Ask what makes both sides the same, or present 12 = 7 + 5."),
    _s("Triangle angle sum", "Geometry", "A triangle has angles 60° and 60°. Find the third.", "60° — equilateral triangles have three 60° angles.", "A familiar case is recognised without using the general angle-sum property.", "Change one given angle to 50° and ask what remains invariant.", True),
    _s("When Pythagoras applies", "Geometry", "A triangle has sides 3 cm, 4 cm and 5 cm. When can Pythagoras be used?", "It finds missing sides in any triangle.", "The theorem is detached from its right-angle condition.", "Show a non-right triangle and ask what feature licenses the equation."),
    _s("Circumference and area", "Geometry", "Find the circumference of a circle with radius 5 cm.", "25π — use π × 5².", "Two circle formulae are remembered but not connected to what they measure.", "Compare what is measured with string and tiles, including cm and cm²."),
    _s("‘Tails is due’", "Probability", "A fair coin has landed heads four times. What is more likely next?", "Tails — it is due.", "Long-run balance is assumed to force short sequences to self-correct.", "Ask what the coin can know about previous tosses."),
    _s("Median with an even set", "Statistics", "Find the median of 2, 4, 6 and 10.", "There is no median; there is no single middle value.", "The two-middle case is unresolved.", "Ask for a value that balances the two middle positions."),
    _s("Mean and mode", "Statistics", "Scores are 10, 10, 10, 10 and 50. What is the mean?", "10 — most people scored 10.", "Mean is confused with mode; all averages are treated alike.", "Ask what each pupil gets if the total is shared equally."),
    _s("Enlargement and area", "Geometry", "A 3 × 4 rectangle is enlarged by scale factor 2. What happens to area?", "It doubles; the sides become 6 and 8.", "A linear scale factor is applied directly to area.", "Calculate both areas and explain why two factors of 2 appear."),
    _s("Similar shapes", "Geometry", "Sides 3 and 6 correspond. What matches a side of 5?", "8 — add 3 again.", "Similarity is treated as a constant additive increase.", "Compare ratios of corresponding side pairs."),
    _s("Index laws", "Algebra", "Simplify x² + x³.", "x⁵ — add the powers.", "A multiplication index law is applied to addition.", "Expand the powers and compare x² × x³ with x² + x³."),
    _s("Zero index", "Algebra", "Evaluate 5⁰.", "0 — anything multiplied by zero is zero.", "The exponent is read as a multiplier, not a count of factors.", "Continue the pattern 5³, 5², 5¹ by repeated division."),
    _s("Coordinates", "Geometry", "Plot (2, -4).", "The point (-4, 2) is plotted.", "Horizontal and vertical roles are known but the ordered pair is reversed.", "Hold the first coordinate at 2 across several points and notice the pattern."),
    _s("Bounds and rounding", "Number", "A length is 8 cm to the nearest centimetre. Give its bounds.", "From 7 cm to 9 cm.", "Nearest centimetre is read as a whole centimetre either side.", "Place 7.4, 7.5, 8.4 and 8.5 on a number line and round each."),
    _s("Algebraic cancellation", "Algebra", "Simplify (x + 4)/x.", "4 — cancel the x.", "Cancellation is attempted across a sum rather than common factors.", "Compare (4x)/x and (x + 4)/x by substituting x = 2."),
    _s("Horizontal line", "Geometry", "Give the equation of the horizontal line through (3, 5).", "x = 5.", "The constant coordinate is remembered but x and y are swapped.", "Name three points on the line and compare their coordinates."),
    _s("Recurring decimal", "Number", "Compare 0.999… with 1.", "It is slightly less; there is always a tiny gap.", "An infinite decimal is treated as an unfinished finite process.", "Ask for the decimal representation of the gap, or use 1/3 × 3."),
    _s("Compound probability", "Probability", "A fair coin is tossed twice. What is P(two heads)?", "1/2 — there are still only heads or tails.", "A one-toss sample space is reused for a two-stage event.", "List HH, HT, TH and TT, then identify the event."),
    _s("Surface area and volume", "Geometry", "Find the volume of a cube with side 3 cm.", "54 — six faces times 3².", "Surface area is calculated and labelled as volume.", "Ask whether paint or filling material is measured; compare cm² with cm³."),
    _s("Circle area: same result", "Geometry", "Find the area of a circle with radius 2 units.", "4π — I used 2πr because it looked easier.", "Circumference and area formulae are not distinguished; r = 2 hides the error.", "Change the radius to 3 and ask for both measures with units.", True),
    _s("Fractions of unequal parts", "Fractions", "What fraction of the shown circle is shaded?", "1/3 — one of the three parts is shaded.", "The denominator counts regions even though their areas are unequal.", "Ask whether three people receiving the regions would get equal amounts."),
    _s("Median before ordering", "Statistics", "Find the median of 3, 7, 4, 2 and 9.", "4 — it is in the middle of the written list.", "Written position is used without ordering; 4 happens to remain the median.", "Rearrange the same numbers and ask whether the median changes.", True),
    _s("Ordering decimals by digit length", "Number", "Order 0.52, 0.714 and 0.3.", "0.3, 0.52, 0.714 — because 3 < 52 < 714.", "Digits after the point are treated as whole numbers; this set masks weak place value.", "Insert 0.08 or compare 0.4 with 0.35 on a place-value chart.", True),
    _s("Square area and perimeter", "Geometry", "Find the area of a square with side 4 units.", "16 — add 4 + 4 + 4 + 4.", "Perimeter is calculated and labelled area; side 4 makes both values equal.", "Change the side to 5 and ask for both measures with their units.", True),
)

STRANDS = ("All strands",) + tuple(sorted({item.strand for item in SCENARIOS}))


def filtered_scenarios(strand: str, case_type: str) -> list[MisconceptionScenario]:
    matches = [item for item in SCENARIOS if strand == "All strands" or item.strand == strand]
    if case_type == "Accidentally correct":
        return [item for item in matches if item.accidental]
    if case_type == "Incorrect answer":
        return [item for item in matches if not item.accidental]
    return matches


def question_ladder(scenario: MisconceptionScenario) -> tuple[tuple[str, str, str], ...]:
    return (
        ("1", "Elicit", "Talk me through how you decided. What does each part of your working mean?"),
        ("2", "Clarify", "Can you show that idea in a different way — with a diagram, example or substitution?"),
        ("3", "Contrast", scenario.contrast),
        ("4", "Reconcile", "How does that result fit with your first explanation? What would you keep or change?"),
        ("5", "Generalise", "What idea would work every time, and how could you check it on a new example?"),
    )


def _reset_rehearsal() -> None:
    for key in ("misconception_first_probe", "misconception_follow_up", "misconception_transfer"):
        st.session_state[key] = ""
    st.session_state.misconception_revealed = False


def _label(item: MisconceptionScenario) -> str:
    return item.title + (" · accidentally correct" if item.accidental else "")


def render_questioning_for_misconceptions() -> None:
    st.markdown("""
    <style>
      .mq-hero{background:linear-gradient(135deg,#17233d,#294fbf 64%,#0f766e);border-radius:1.25rem;color:white;padding:2rem 2.2rem;margin-bottom:1.2rem;box-shadow:0 16px 40px rgba(22,35,61,.16)}
      .mq-hero .eyebrow{color:#b9caff;font-size:.73rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase}.mq-hero h1{color:white;margin:.55rem 0 .7rem;font-size:clamp(2rem,4vw,3.2rem)}.mq-hero p{color:#e8edff;margin:0;max-width:48rem;line-height:1.55}
      .mq-student{background:#fff;border:1px solid #dce3ee;border-left:6px solid #f59e0b;border-radius:1rem;padding:1.15rem 1.3rem;margin:.5rem 0 1rem;box-shadow:0 8px 24px rgba(31,45,73,.05)}.mq-student small{color:#8a4b08;font-weight:800;letter-spacing:.12em}.mq-student div{color:#152033;font-size:1.22rem;font-weight:750;margin-top:.4rem}
      .mq-card{background:#f5f8ff;border:1px solid #d9e2ff;border-radius:1rem;padding:1rem 1.15rem;height:100%}.mq-card small{color:#3157d5;font-weight:800;letter-spacing:.1em}.mq-step{display:flex;gap:.75rem;align-items:flex-start;margin:.8rem 0}.mq-step i{background:#e7edff;color:#294fbf;border-radius:99px;display:inline-flex;align-items:center;justify-content:center;min-width:1.75rem;height:1.75rem;font-style:normal;font-weight:800}.mq-step span{color:#5f6b7a;line-height:1.45}.mq-step b{color:#152033}
    </style>
    <section class="mq-hero"><div class="eyebrow">Deliberate practice · diagnostic questioning</div><h1>Question the reasoning, not the answer.</h1><p>Correct answers can conceal insecure thinking. Rehearse questions that make a pupil's model visible before explaining, correcting or supplying a rule.</p></section>
    """, unsafe_allow_html=True)

    metrics = st.columns(3)
    metrics[0].metric("Scenario bank", f"{len(SCENARIOS)} cases")
    metrics[1].metric("Accidentally correct", f"{sum(item.accidental for item in SCENARIOS)} cases")
    metrics[2].metric("Practice sequence", "5 question moves")

    st.markdown("## Choose a misconception")
    left, right = st.columns(2)
    strand = left.selectbox("Mathematical strand", STRANDS, key="misconception_strand")
    case_type = right.selectbox("Answer type", ("All cases", "Accidentally correct", "Incorrect answer"), key="misconception_case_type")
    matches = filtered_scenarios(strand, case_type)
    if not matches:
        st.info("There are no scenarios with that combination yet. Choose another strand or answer type.")
        return
    selected = st.selectbox("Scenario", matches, format_func=_label, key="misconception_scenario", on_change=_reset_rehearsal)
    kind = "Accidentally correct — inspect the method" if selected.accidental else "Incorrect answer — diagnose before correcting"
    st.caption(f"{selected.strand} · {kind}")

    practise, diagnostic, ladder = st.tabs(("Rehearse", "Diagnostic map", "Question ladder"))
    with practise:
        st.markdown("### 1 · Notice the evidence")
        st.write(f"**Task:** {selected.prompt}")
        st.markdown(f'<div class="mq-student"><small>STUDENT SAYS</small><div>“{selected.response}”</div></div>', unsafe_allow_html=True)
        if selected.accidental:
            st.warning("The answer is correct. Find out whether the reasoning survives a changed example.")
        st.markdown("### 2 · Draft a diagnostic sequence")
        st.caption("Start by eliciting. Delay explanation, reminders and rules until the pupil's thinking is visible.")
        st.text_area("Your first probe", placeholder="Talk me through how you decided…", key="misconception_first_probe")
        col1, col2 = st.columns(2)
        col1.text_area("Follow-up", placeholder="Probe a choice, representation or inconsistency…", key="misconception_follow_up")
        col2.text_area("Transfer check", placeholder="Vary one feature so the misconception cannot hide…", key="misconception_transfer")
        if st.button("Reveal the misconception", type="primary", width="stretch"):
            st.session_state.misconception_revealed = True
        if st.session_state.get("misconception_revealed", False):
            st.success("Now compare your sequence with the Diagnostic map and Question ladder.")

    with diagnostic:
        if not st.session_state.get("misconception_revealed", False):
            st.info("Draft your probes in Rehearse, then reveal the misconception.")
        else:
            st.markdown("### What the response may be hiding")
            cols = st.columns(3)
            content = (("CURRENT MODEL", selected.thinking), ("KNOWLEDGE TO PRESERVE", "The response contains a usable fragment of knowledge. Name it before challenging the connection or generalisation."), ("DIAGNOSTIC GOAL", "Establish the pupil's meaning and whether their method transfers; do not infer understanding from answer accuracy alone."))
            for column, (heading, copy) in zip(cols, content):
                column.markdown(f'<div class="mq-card"><small>{heading}</small><p>{copy}</p></div>', unsafe_allow_html=True)
            st.markdown("#### A high-value variation")
            st.write(selected.contrast)
            st.caption("Vary one feature at a time. The aim is evidence about the model, not difficulty for its own sake.")

    with ladder:
        st.markdown("### A five-move question ladder")
        st.caption("Use this flexibly and stop when the pupil's reasoning is clear.")
        for number, move, question in question_ladder(selected):
            st.markdown(f'<div class="mq-step"><i>{number}</i><span><b>{move}</b><br>{question}</span></div>', unsafe_allow_html=True)
        st.divider()
        st.markdown("#### Listen for")
        st.write("A changed explanation, not merely a changed answer: the pupil can name what the first method assumed, use new evidence and state an idea that transfers.")
        st.markdown("#### Avoid too soon")
        st.write("‘Are you sure?’, binary checks, supplying the formula, naming the misconception for the pupil, or choosing another example that preserves the same accidental answer.")
