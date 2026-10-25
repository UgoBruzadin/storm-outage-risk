"""Publish to Hugging Face: the app's data as a dataset, the app as a Space.

  pixi run publish-data    upload data/app/*  ->  dataset  <user>/storm-outage-risk-data
  pixi run deploy-space    upload the app     ->  Space    <user>/storm-outage-risk  (Docker)

Both repos are created PRIVATE unless you pass --public. Only small files
leave your machine: the ~8 MB of Parquet in data/app/, and the app code —
never the raw data or the warehouse.

Needs a Hugging Face access token with write permission, in the environment
or in a git-ignored .env file:  HF_TOKEN=hf_...   (never commit it)

The Space reads the dataset at run time (APP_DATA = hf://datasets/...). For a
private dataset, add HF_TOKEN as a *secret* in the Space settings (a read
token is enough) — the deploy step reminds you.
"""
import argparse
import os
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent
DATASET_NAME = "storm-outage-risk-data"
SPACE_NAME = "storm-outage-risk"

DATASET_CARD = """---
license: other
pretty_name: Storm Outage Risk — app data
---
# Storm Outage Risk — app data

Small Parquet outputs read by the Storm Outage Risk dashboard: per-region
resilience metrics and shapes, 2025 model predictions per 6-hour block, top
storms, feature importance and evaluation metrics. Built from public data:

- U.S. DOE / ORNL EAGLE-I recorded electricity outages (cite with the
  citation files shipped with the EAGLE-I download)
- NOAA HRRR (via Open-Meteo), NOAA Storm Events
- USFS / NLCD Tree Canopy Cover, U.S. Census ACS and TIGER boundaries
"""

SPACE_CARD = """---
title: Storm Outage Risk
emoji: ⚡
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 8501
pinned: false
---
Which Missouri & Illinois counties lose power when storms hit — and why?
Source: https://github.com/{github}
"""


def load_dotenv():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def publish_data(api, user, private):
    repo = f"{user}/{DATASET_NAME}"
    api.create_repo(repo, repo_type="dataset", private=private, exist_ok=True)
    data = ROOT / "data" / "app"
    files = sorted(p.name for p in data.iterdir())
    if not {"regions.parquet", "predictions.parquet", "meta.json"} <= set(files):
        raise SystemExit("data/app/ is incomplete — run `pixi run export-app` first")
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(data, tmp, dirs_exist_ok=True)
        Path(tmp, "README.md").write_text(DATASET_CARD)
        info = api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=tmp,
                                 commit_message="Update app data")
    print(f"dataset: https://huggingface.co/datasets/{repo}  (revision {info.oid[:10]}, files: {files})")


def deploy_space(api, user, private, github):
    repo = f"{user}/{SPACE_NAME}"
    api.create_repo(repo, repo_type="space", space_sdk="docker", private=private, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for item in ["Dockerfile", "pixi.toml", "pixi.lock", ".dockerignore"]:
            shutil.copy(ROOT / item, tmp)
        for folder in ["app", ".streamlit"]:
            shutil.copytree(ROOT / folder, Path(tmp, folder), ignore=shutil.ignore_patterns("__pycache__"))
        Path(tmp, "data", "app").mkdir(parents=True)        # the image reads the dataset instead
        Path(tmp, "data", "app", ".gitkeep").touch()
        Path(tmp, "README.md").write_text(SPACE_CARD.format(github=github))
        api.upload_folder(repo_id=repo, repo_type="space", folder_path=tmp, commit_message="Deploy app")
    api.add_space_variable(repo, "APP_DATA", f"hf://datasets/{user}/{DATASET_NAME}")
    print(f"space: https://huggingface.co/spaces/{repo}")
    print("If the dataset is private: Space settings -> Secrets -> add HF_TOKEN (a read token).")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("what", choices=["data", "space"])
    parser.add_argument("--public", action="store_true", help="create the repo public (default: private)")
    parser.add_argument("--github", default="UgoBruzadin/storm-outage-risk")
    args = parser.parse_args()

    load_dotenv()
    if not os.environ.get("HF_TOKEN"):
        raise SystemExit("Set HF_TOKEN (environment or .env) to a Hugging Face write token.")
    api = HfApi(token=os.environ["HF_TOKEN"])
    user = api.whoami()["name"]
    if args.what == "data":
        publish_data(api, user, private=not args.public)
    else:
        deploy_space(api, user, private=not args.public, github=args.github)


if __name__ == "__main__":
    main()
