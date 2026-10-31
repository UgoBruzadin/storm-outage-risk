# app/

The Streamlit dashboard: `pixi run app` → http://localhost:8501 (after `pixi run export-app` and
`pixi run python -m ml.export_hourly`).

Organised by the decision each page supports, for a non-technical reader:

- `views/storm_room.py` — a 2025 storm hour by hour, two hours ahead: counties on alert, a "stage crews here" list
  (CSV download) and, on request, what happened.
- `views/alert_level.py` — how many alerts to act on: outages caught, alerts that were real, call-outs and net savings,
  against the official forecasts, with the best level for the chosen cost assumptions.
- `views/trust.py` — the 2025 test year in plain terms: against the official forecasts, storm by storm, county by
  county, and whether its chances come true.
- `views/scorecard.py` — which counties keep losing power, 2020–2025.
- `views/about.py` — how it works, with links to the write-up and the experiment log.

Every word on the pages is in `text.yaml` (placeholders like `{ratio}` are filled from the data). `lib.py` holds data
loading (local `data/app/`, or `APP_DATA=hf://datasets/...` with `HF_TOKEN` for a private dataset), the text helper and
chart styling (one validated palette, light and dark). Pages are in `views/`, not `pages/`: a `pages/` folder triggers
Streamlit's older automatic navigation.

It reads only precomputed files and never runs the model. Tests: `../tests/test_app.py` renders every page from a small
synthetic fixture (`../tests/conftest.py`) and checks every text key exists.
