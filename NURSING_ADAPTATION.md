# Nursing Student Adaptation — Design Note

## Purpose

Adapt the virtual-classroom architecture into a supervised nursing-education
simulation. The application should predict how an entirely synthetic patient
responds to a nursing student's words or selected action. It should not grade,
coach or judge the nursing student; interpretation and assessment remain with
the supervising educator.

## Essential architecture

The nursing version must keep two systems separate:

1. **Deterministic clinical-state engine** — controls observations, symptoms,
   prescribed treatment effects, time-dependent deterioration and clinical
   outcomes using educator-authored rules.
2. **AI patient-reaction engine** — controls only dialogue, emotion, response
   latency and visible behaviour within the clinical state supplied to it.

Generative AI must never invent physiology, diagnoses, medication doses,
contraindications or the outcome of an intervention.

## Existing features that can be reused

| Classroom feature | Nursing adaptation |
| --- | --- |
| Pupil profile | Synthetic patient profile |
| Class selection | Ward, community or specialist setting |
| Student Simulator | One-to-one patient interaction |
| Academic AfL | History-taking, explanation or handover practice |
| Observe Learning | Ward observation or care-round simulation |
| Seating plan | Bed-space, caseload or community-visit map |
| Lesson sequence | Patient journey or changing clinical condition |
| Teacher stimulus | Nursing student's spoken words or selected action |
| Pupil reaction | Patient's verbal and visible response |
| Replay scenario | Restart from the same clinical and emotional state |

## Temporary scenario controls

Controls should start at **Natural**, affect the current simulation only and
never alter the underlying patient case:

- Engagement and willingness to communicate
- Anxiety or distress
- Pain expression
- Processing and communication latency
- Health literacy
- Independence with activities of daily living
- Trust and willingness to disclose
- Cognitive clarity
- Symptom severity

## Patient reactions to support

- Quiet or minimal engagement
- Uncertainty about medical history
- Questioning or challenging information
- Declining medication, observations or personal care
- Confident health misconception
- Distraction caused by pain, anxiety or the environment
- Agreeing verbally but not beginning an action
- Guarded disclosure
- Embarrassment around personal care
- Difficulty understanding an explanation
- Repeated reassurance-seeking
- Increasing confusion
- Pain-related irritability
- Breathlessness limiting speech
- Withdrawal of consent

All reactions should remain proportionate, stateful and grounded in the
authored patient case. The interface should display what the patient says and
does without deciding whether the student's action was good or bad.

## Safety and inclusion constraints

- Use fictional or formally approved anonymised patient cases only.
- Language needs may affect communication or the need for an interpreter, not
  intelligence.
- Cognitive impairment, neurodiversity, hearing or visual impairment may shape
  access only when explicitly present in the case.
- Ethnicity must not be used to infer behaviour, pain tolerance, adherence,
  motivation or trust.
- Social circumstances should influence a scenario only when explicitly
  authored, relevant and appropriate for the learning objective.
- Safety-critical clinical rules must be testable without calling an AI model.
- The supervising educator controls feedback, evaluation and assessment.

## Suggested first version

Begin with one field, probably adult nursing, and approximately six synthetic
patients. Initial scenarios could cover:

- Pain assessment
- Consent and withdrawal of consent
- Medication explanation
- Personal care and dignity
- Confusion or delirium
- Recognition of deterioration
- Discharge understanding

Each scenario should define its learning context, starting clinical state,
permitted student stimuli/actions, deterministic state transitions, visible
patient cues and replay conditions before any AI dialogue is generated.

## Standards context

- [NMC simulated practice learning guidance](https://www.nmc.org.uk/standards/guidance/supporting-information-for-our-education-and-training-standards/simulated-practice-learning/)
- [The NMC Code](https://www.nmc.org.uk/standards/code/read-the-code-online/)

This note records a possible future direction. It does not mean the current
classroom application has been converted for clinical education.
