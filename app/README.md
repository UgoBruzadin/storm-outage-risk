# app/

The Streamlit dashboard: `pixi run app` → http://localhost:8501 (after `pixi run export-app`).

- `streamlit_app.py` — navigation; `pages/` — Overview map, Storm replay, Resilience scorecard, Model.
- `lib.py` — data loading (local `data/app/` or `APP_DATA=hf://datasets/...`; `HF_TOKEN` for a
  private dataset) and chart styling (one validated palette, light + dark).

It reads only precomputed files and never runs the model. Tests: `../tests/test_app.py`.
