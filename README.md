# Butler Academy Teaching Studio

A Streamlit workspace for knowing a class, planning a lesson and rehearsing
high-leverage teaching moves with a virtual cohort.

## What is included

- Student search and cohort passports
- Cohort analytics and printable reports
- Seating planning with pupil-context indicators
- Stateful virtual pupil-reaction roleplay with replay
- Academic AfL rehearsal
- Lesson stress-testing
- Sequence-of-learning evaluation
- Simulated circulation and learning observation

## Run locally

Use Python 3.11 or newer.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

For AI features, copy `.streamlit/secrets.toml.example` to
`.streamlit/secrets.toml` and add `GEMINI_API_KEY`, `OPENAI_API_KEY`, or both.
Use the Options page to choose Gemini or OpenAI. The same page can scale
how Participation, Academic Confidence, Processing Speed, Independence and
Answer Security are expressed in newly generated interactions. Every control
starts in the centre at **Natural**. The optional teaching-example focus can
make one of these mild reactions easier to demonstrate:

- Quiet non-participation
- “I don’t know” followed by withdrawal
- Public challenge to an instruction
- Task refusal
- Confident misconception
- Peer distraction during discussion
- Agreement without beginning the task

These are temporary scenario controls, not edits to a pupil record. The app
always retains the published spreadsheet values and never writes the controls
back to the Google Sheet. When a selected reaction lacks direct profile support,
the interface labels it as a hypothetical teaching example. SEND detail may
shape access, processing or communication only when relevant; EAL may shape
language and response latency. Pupil Premium and ethnicity are never used to
infer behaviour or attainment.

The shared reaction engine is used by the Simulator, Academic AfL, Observe
Learning, and the named-pupil predictions in the lesson and sequence tools. It
predicts pupil-visible behaviour only and does not grade, coach or judge the
teacher. Simulator reactions remain mild and stateful. **Replay scenario**
returns to the same starting state and preserves the previous series for a
like-for-like retry; **New variation** clears the replay cache.

The class-information and planning views work without either API key, and
secrets should never be pasted into the Python source.

To enable explicit seating-plan persistence, also configure
`SEATING_PLAN_STORAGE_PATH` in `secrets.toml`. The example uses the ignored
local `.data/` directory for development; deployments should point it at an
approved durable school storage mount. Printable HTML and JSON exports contain
pupil names and must remain inside the approved environment.

## Project shape

```text
app.py                       Main navigation and page composition
config.py                    App, cohort and subject configuration
modules/app_shell.py         Shared design system, navigation and home page
modules/class_setup.py       Reusable subject and class controls
modules/data_loader.py       Cached remote spreadsheet loading
modules/data_utils.py        Testable data normalisation and filters
modules/reaction_engine.py   Shared stateful pupil-reaction rules and replay cache
modules/simulation_options.py Temporary interaction scenario controls
modules/photo_utils.py       Cached pupil-photo processing
modules/*                    Existing teaching tools
photos/                      Local pupil images
tests/                       Fast tests for shared data behaviour
```

## Add the next feature

1. Put the feature’s rendering code in a focused module under `modules/`.
2. Add its label to `NAV_ITEMS` and `NAV_LABELS` in `modules/app_shell.py`.
3. Add one matching branch in `app.py`, reusing
   `render_subject_class_setup()` when the feature needs a class.
4. Keep spreadsheet cleanup and non-UI filters in `modules/data_utils.py` so
   they remain easy to test.

Do not commit `.streamlit/secrets.toml` or export pupil data outside the
school’s approved environment.
