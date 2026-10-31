"""Back up the hard-to-rebuild data to a PRIVATE Hugging Face dataset.

  pixi run backup-hf     data/raw/ (EAGLE-I, weather, forecasts, NWS, geo, Census) and a warehouse snapshot
                         ->  private dataset  <user>/storm-outage-risk-backup

Private on purpose: EAGLE-I has its own terms, so the raw files are backed up, never republished. Uploads only
send files that changed, so re-running after a new download is cheap. The free tier includes
100 GB of private storage; this is ~17 GB.

Needs a Hugging Face token with write permission, in the environment or in the git-ignored .env file at the repo
root (HF_TOKEN=hf_...), or a saved `hf auth login`.
"""
import os

from huggingface_hub import HfApi
from publish_hf import ROOT, load_dotenv

REPO_NAME = "storm-outage-risk-backup"
CARD = """---
license: other
pretty_name: Storm Outage Risk — private data backup
---
# Storm Outage Risk — private data backup

A private backup of the raw downloads (DOE / ORNL EAGLE-I outages, HRRR weather and forecasts, NWS warnings, SPC
outlooks, geography, Census) and a DuckDB warehouse snapshot for github.com/UgoBruzadin/storm-outage-risk.
Not for redistribution: each source keeps its own terms.
"""


def main():
    load_dotenv()
    api = HfApi(token=os.environ.get("HF_TOKEN"))
    user = api.whoami()["name"]
    repo = f"{user}/{REPO_NAME}"
    api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
    api.upload_file(path_or_fileobj=CARD.encode(), path_in_repo="README.md", repo_id=repo, repo_type="dataset")

    # one commit per source folder (eaglei, weather, nws, ...), so an interruption costs at most one folder;
    # content the repo already has is not sent again, so re-running only uploads what changed
    raw = (ROOT / "data" / "raw").resolve()                       # data/raw may be a link to another folder
    for folder in sorted(p for p in raw.iterdir() if p.is_dir()):
        print(f"uploading raw/{folder.name}", flush=True)
        api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=folder, path_in_repo=f"raw/{folder.name}",
                          commit_message=f"Back up raw/{folder.name}")
    print("uploading the warehouse snapshot", flush=True)
    api.upload_file(path_or_fileobj=str(ROOT / "data" / "warehouse.duckdb"), path_in_repo="warehouse/warehouse.duckdb",
                    repo_id=repo, repo_type="dataset", commit_message="Warehouse snapshot")
    print(f"done: https://huggingface.co/datasets/{repo} (private)", flush=True)


if __name__ == "__main__":
    main()
