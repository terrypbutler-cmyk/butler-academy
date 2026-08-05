# Initial Data Improvement Plan

Saved: 27 July 2026

Source: [Virtual Students Google Sheet](https://docs.google.com/spreadsheets/d/11labvJRxO3GZ6IF2JkPmlZvKAUrdwjiHWcB_030KkJY/edit)

## What is already working well

- Both cohort tabs contain 70 pupils.
- Student IDs and names match across both tabs.
- There are no duplicate student IDs or full names.
- Year 9 option-subject grades and subject reports are consistently paired.
- Attendance, suspension and voice fields are complete in the Year 9 data.
- Core reports are present for every pupil.

## Priority improvements

### 1. Resolve the year-group mismatch

The second spreadsheet tab is named `year9`, and its form groups are
`9-Dart`, `9-Plym` and `9-Tamar`. The app currently presents this data as
Year 10 and describes the pupils as approximately 15 years old.

Decide whether the cohort is Year 9 or Year 10, then align:

- the spreadsheet tab name;
- form-group values;
- app navigation and headings;
- age and Key Stage information sent to Gemini;
- reports, filters and filenames.

### 2. Send the selected subject grade to Gemini

The spreadsheet stores subject-specific fields such as
`Maths Predicted Grade` and `Eng Lit Predicted Grade`. The AI modules currently
look only for a generic `Projected Grade` or `Predicted Grade`, so they can send
`None recorded` instead of the pupil's actual subject grade.

Update the app to map the selected subject to the correct predicted-grade
column. Science should use an agreed rule for `Sci 1 Predicted Grade` and
`Sci 2 Predicted Grade`.

### 3. Standardise columns and missing values

- Use `Student ID` consistently instead of mixing `Student ID` and `ID`.
- Give the blank Year 9 picture column an explicit heading or remove it.
- Standardise `SAT's Maths`, `SATs Maths` and `KS2 Maths`.
- Remove trailing spaces from predicted-grade headings.
- Standardise `Sciences`/`Science` and `PE`/`Sport`.
- Five Year 7 pupils have a SEND detail but no SEN status.
- Three Year 7 baseline-score cells contain `B` in numeric columns. Use a
  separate status such as `Baseline unavailable` and leave the score blank.
- Populate or remove the Year 9 `Tutor` column, which is currently empty for
  all 70 pupils.
- Use one missing-value convention rather than mixing blanks and `N/A`.

### 4. Add concise simulation fields

Add structured fields that directly affect a simulated classroom response:

- `Preferred Name`
- `Pronouns`
- `Participation Level`
- `Academic Confidence`
- `Processing Time`
- `Independence`
- `Peer Discussion Style`
- `Cold Call Response`
- `Common Misconception`
- `Current Learning Target`
- `Helpful Scaffold`
- `AI-safe Context`
- `Voice_Name` for Year 7

Use short controlled values where possible, such as `Low`, `Medium` and
`High`, with data-validation dropdowns.

### 5. Make reports neutral and evidence based

Replace fixed judgements with observable classroom behaviour.

Example:

- Avoid: `Arrogant and refuses to listen.`
- Prefer: `Frequently speaks over peers and benefits from explicit
  turn-taking prompts.`

Use a consistent pattern:

1. observable strength;
2. observable barrier;
3. classroom effect;
4. effective support;
5. current next step.

### 6. Minimise sensitive information sent to AI

The complete sheet can retain authorised pastoral information, but Gemini
should receive only what is needed for the current simulation.

Do not routinely send:

- student IDs;
- exact dates of birth;
- ethnicity;
- detailed family circumstances;
- detailed trauma histories;
- unrelated suspension information.

Create a short `AI-safe Context` field containing only relevant, neutral
classroom information. Do not infer pupil mood or behaviour from ethnicity,
home life, disability or disadvantage.

## Recommended spreadsheet structure

### Students

One row per pupil containing stable class, attainment and adjustment data.

### Subject Profiles

One row per pupil and subject containing:

- Student ID
- Subject
- Enrolled
- Current or predicted grade
- Strength
- Common misconception
- Current learning target
- Helpful scaffold

### Simulation Traits

One row per pupil containing the concise interaction fields used by the
simulator, including confidence, participation, processing time, peer-response
style and voice ID.

## Suggested order for tomorrow

1. Decide whether the second cohort is Year 9 or Year 10.
2. Make a copy of the Google Sheet before restructuring it.
3. Standardise headings and missing values.
4. Add preferred-name, pronoun and AI-safe-context fields.
5. Build the `Subject Profiles` structure.
6. Update the app to retrieve the selected subject's grade and profile.
7. Stop using home-life and suspension information to generate random moods.
8. Test five contrasting pupils in Academic AfL before rolling the changes
   across the whole dataset.

