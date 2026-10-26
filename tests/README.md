# tests/

`pixi run pytest -q` (CI runs it too). `conftest.py` writes a small synthetic fixture of the app dataset to a temp
folder, so tests never need the real data; `test_app.py` renders every dashboard page with
Streamlit's AppTest. Data tests live in dbt (`pixi run dbt test`).
