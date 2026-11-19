"""A neural network on the headline's inputs (docs/experiments.md, E57a).

E1 compared tree libraries, never a neural network. Trees usually win on tables, but a network makes different
mistakes, so averaging the two may gain. Same rows, inputs and label as the headline (E55's 110 inputs, 2 hours
ahead, new outages, trained on the weather that actually happened and fed HRRR forecasts when scored).

The network
  inputs     the numeric inputs rank-transformed to a normal shape (CAPE and rain are heavy-tailed), fitted on the
             training rows; a missing value becomes 0 plus a 0/1 flag. Month, hour, SPC category, state and county
             are learned embeddings (county: 16 numbers, dropped to "unknown" for 10% of training rows so the network
             also works for a county it hasn't seen)
  layers     512-256-128, SiLU, LayerNorm, dropout 0.2, one output (the log-odds)
  training   cross-entropy weighted by the sampling weights (data.sampled_years), so chances stay on the scale of
             the full table (no focal loss); AdamW, batch 8,192, a cosine schedule over MAX_EPOCHS

  select  trained on 2020-2023; the number of epochs is the one with the best mean PR-AUC over the seeds on 2024
          (all of 2024's outages, 10% of the rest, weighted). Then every 2024 decision is scored with the newest HRRR
          run (as E55) and compared with E55's XGBoost trained here on the same rows, by E55's rule: kept if the gain
          (seed-mean chances) has a 95% storm-day range above zero and at least 2 of 3 seeds are better
            network                 alone
            network + XGBoost       the two chances averaged
  test    both refitted on 2020-2024 (the network for the chosen number of epochs) and scored once on every 2025
          decision with the mean of the five HRRR runs issued 2-6 hours before, as the headline

Usage: pixi run -e nn python -m ml.nn_tabular select | test [--smoke]
  --smoke   the two-state copy in data/smoke/root (ml/smoke.py; build it with `pixi run pipeline --smoke` once),
            2 epochs and 5-tree XGBoost: every line runs in minutes
Writes ml/results/nn_2024.csv (+ nn_2024_epochs.csv) and nn_2025.csv; models and chances
under data/cache/nn/ (a stopped run reuses fitted models).
"""
import os
import sys
from pathlib import Path

if "--smoke" in sys.argv:                  # before ml.data reads STORM_ROOT
    os.environ.setdefault("STORM_ROOT", str(Path(__file__).resolve().parent.parent / "data" / "smoke" / "root"))
    os.environ["STORM_SMOKE"] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
from sklearn.metrics import average_precision_score  # noqa: E402
from sklearn.preprocessing import QuantileTransformer  # noqa: E402
from torch import nn  # noqa: E402

from ml import data, models  # noqa: E402
from ml import forecast_test as ft  # noqa: E402
from ml.moving_window import FEATURES, PARAMS  # noqa: E402
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day  # noqa: E402

SEEDS = range(3)
MAX_EPOCHS = 2 if data.SMOKE else 20
BATCH, LR, WEIGHT_DECAY, DROPOUT, COUNTY_DROP = 8192, 1e-3, 1e-4, 0.2, 0.1
HIDDEN = (512, 256, 128)
CATEGORIES = ["month", "block_hour_utc", "spc_cat"]           # embedded, not rank-transformed
VAL_NEG = 0.1                                                 # 2024 for picking epochs: every outage, 10% of the rest
OUT = data.ROOT / "data" / "cache" / "nn"
RESULTS = data.ROOT / "ml" / "results"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
NETWORK, XGB, BLEND = "network", "E55 XGBoost", "network + XGBoost"


def features():
    """The headline's inputs (110), as the headline model sees them."""
    return data.resolve_features(FEATURES) + ft.WINDOW


# ---------- inputs ----------

class Prep:
    """Training-fitted transforms: rank -> normal for numeric inputs, missing flags, category codes."""

    def fit(self, df, cols):
        self.numeric = [c for c in cols if c not in CATEGORIES]
        sample = df[self.numeric].sample(min(len(df), 1_000_000), random_state=0).to_numpy(np.float32)
        self.qt = QuantileTransformer(n_quantiles=1000, output_distribution="normal", subsample=10**9,
                                      random_state=0).fit(sample)
        self.flags = [i for i, c in enumerate(self.numeric) if df[c].isna().any()]
        regions = sorted(df.region_fips.astype(str).unique())
        self.county = {r: i + 1 for i, r in enumerate(regions)}                # 0 = unknown
        self.state = {s: i + 1 for i, s in enumerate(sorted({r[:2] for r in regions}))}
        return self

    @property
    def sizes(self):
        return {"n_num": len(self.numeric) + len(self.flags), "n_county": len(self.county) + 1,
                "n_state": len(self.state) + 1}

    def transform(self, df):
        """-> (numeric float32 [n, n_num], categories int64 [n, 5]: month, hour, SPC, state, county)."""
        x = self.qt.transform(df[self.numeric].to_numpy(np.float32))
        flags = np.isnan(x[:, self.flags]).astype(np.float32)
        x = np.nan_to_num(x, nan=0.0).astype(np.float32)
        fips = df.region_fips.astype(str)
        cats = np.column_stack([
            df.month.to_numpy() - 1, df.block_hour_utc.to_numpy(),
            np.nan_to_num(df.spc_cat.to_numpy(dtype=float), nan=-1) + 1,              # 0 = no outlook
            fips.str[:2].map(self.state).fillna(0).to_numpy(), fips.map(self.county).fillna(0).to_numpy(),
        ]).astype(np.int64)
        return np.hstack([x, flags]), cats


# ---------- the network ----------

class Net(nn.Module):
    def __init__(self, n_num, n_county, n_state):
        super().__init__()
        self.emb = nn.ModuleList([nn.Embedding(12, 4), nn.Embedding(24, 6), nn.Embedding(8, 4),
                                  nn.Embedding(n_state, 8), nn.Embedding(n_county, 16)])
        layers, width = [], n_num + 4 + 6 + 4 + 8 + 16
        for h in HIDDEN:
            layers += [nn.Linear(width, h), nn.LayerNorm(h), nn.SiLU(), nn.Dropout(DROPOUT)]
            width = h
        self.body = nn.Sequential(*layers)
        self.head = nn.Linear(width, 1)

    def forward(self, num, cats):
        z = torch.cat([num] + [e(cats[:, i]) for i, e in enumerate(self.emb)], dim=1)
        return self.head(self.body(z)).squeeze(1)


def predict(net, num, cats):
    net.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(num), 65_536):
            n = torch.from_numpy(num[i:i + 65_536]).to(DEVICE)
            c = torch.from_numpy(cats[i:i + 65_536]).to(DEVICE)
            out.append(torch.sigmoid(net(n, c)).float().cpu().numpy())
    return np.concatenate(out) if out else np.zeros(0, np.float32)


def train_net(num, cats, y, w, seed, epochs, sizes, base_rate, val=None, checkpoints=None):
    """Fit for `epochs` epochs of a cosine schedule over MAX_EPOCHS (so a network stopped at the chosen epoch is the
    same whether it trained longer or not). val = (num, cats, y, w): its weighted PR-AUC after each epoch;
    checkpoints: a folder to save the weights after each epoch in. Returns (net, [scores])."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    net = Net(**sizes).to(DEVICE)
    with torch.no_grad():
        net.head.bias.fill_(float(np.log(base_rate / (1 - base_rate))))      # start at the base rate
    opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    steps = MAX_EPOCHS * -(-len(y) // BATCH)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=steps)
    num_t, cats_t = torch.from_numpy(num), torch.from_numpy(cats)
    y_t, w_t = torch.from_numpy(y.astype(np.float32)), torch.from_numpy(w.astype(np.float32))
    loss_fn = nn.BCEWithLogitsLoss(reduction="none")
    scores = []
    for epoch in range(epochs):
        net.train()
        t0 = time.time()
        perm = torch.randperm(len(y))
        for i in range(0, len(y), BATCH):
            idx = perm[i:i + BATCH]
            n, c = num_t[idx].to(DEVICE, non_blocking=True), cats_t[idx].to(DEVICE, non_blocking=True)
            drop = torch.rand(len(idx), device=DEVICE) < COUNTY_DROP            # county -> unknown
            c[:, 4] = torch.where(drop, torch.zeros_like(c[:, 4]), c[:, 4])
            yb, wb = y_t[idx].to(DEVICE), w_t[idx].to(DEVICE)
            loss = (loss_fn(net(n, c), yb) * wb).sum() / wb.sum()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            sched.step()
        if checkpoints is not None:
            torch.save(net.state_dict(), checkpoints / f"net_seed{seed}_epoch{epoch + 1}.pt")
        if val is not None:
            p = predict(net, val[0], val[1])
            scores.append(float(average_precision_score(val[2], p, sample_weight=val[3])))
            print(f"seed {seed} epoch {epoch + 1}: 2024 PR-AUC {scores[-1]:.4f} ({time.time() - t0:.0f}s)", flush=True)
    return net, scores


def fit_xgb(train, cols, seed, path):
    m = models.build("xgboost", PARAMS | {"random_state": seed})
    if path.exists():
        m.load_model(path)
    else:
        m.fit(train[cols], train.y, sample_weight=train.weight)
        m.save_model(path)
    return m


# ---------- the years scored ----------

def newest_run(f):
    """2024 as E55 scored it: the window weather from the run issued 2 hours before each decision."""
    return {"newest": ft.window_from_forecast(f, ft.RUN_AGE)}


def scored_rows(year):
    """Every scored decision of `year`, a state at a time, with its window versions (`<input>|<version>`)."""
    if year == ft.TEST_YEAR:
        return ((rows, ft.RUN_NAMES) for _, rows, _ in ft.states_2025(ft.five_runs, year=year))
    return ((rows, ["newest"]) for _, rows, _ in ft.states_2025(newest_run, year=year, require_actual=False))


def run_mean(rows, versions, cols, score):
    """score(frame of inputs) for each version of the window weather, averaged."""
    return np.mean([score(ft.with_version(rows, cols, v)) for v in versions], axis=0)


def score_year(year, cols, prep, nets, xgbs, val_frac=None):
    """Each seed's network and XGBoost chances for every decision of `year`. val_frac: also return a sample (every
    outage, val_frac of the rest, weighted) as transformed arrays, for picking epochs."""
    parts, val = [], []
    rng = np.random.default_rng(0)
    for rows, versions in scored_rows(year):
        out = rows[["region_fips", "block_start", "y"]].copy()
        fips = rows.region_fips.to_numpy()
        for s, net in nets.items():
            out[f"{NETWORK}|seed{s}"] = run_mean(
                rows, versions, cols, lambda x, net=net, f=fips: predict(net, *prep.transform(x.assign(region_fips=f))))
        for s, m in xgbs.items():
            out[f"{XGB}|seed{s}"] = run_mean(rows, versions, cols, lambda x, m=m: m.predict_proba(x)[:, 1])
        if val_frac is not None:
            keep = (rows.y.to_numpy() == 1) | (rng.random(len(rows)) < val_frac)
            v = ft.with_version(rows[keep], cols, versions[0]).assign(region_fips=rows.region_fips[keep].to_numpy())
            num, cats = prep.transform(v)
            w = np.where(rows.y.to_numpy()[keep] == 1, 1.0, 1 / val_frac)
            val.append((num, cats, rows.y.to_numpy()[keep], w))
        parts.append(out)
        print(f"{year}: {len(out):,} decisions scored", flush=True)
    pred = pd.concat(parts, ignore_index=True)
    if val_frac is None:
        return pred
    return pred, tuple(np.concatenate([v[i] for v in val]) for i in range(4))


def validation_sample(year, cols, prep):
    """Every outage of `year` and VAL_NEG of the rest (weighted), newest run, transformed: for picking epochs."""
    return score_year(year, cols, prep, {}, {}, val_frac=VAL_NEG)[1]


def add_blend(pred, seeds):
    for s in seeds:
        pred[f"{BLEND}|seed{s}"] = (pred[f"{NETWORK}|seed{s}"] + pred[f"{XGB}|seed{s}"]) / 2
    return pred


def judge(pred, seeds, year):
    """E55's rule for each arm against E55's XGBoost: gain of the seed-mean chances with a storm-day range, and how
    many seeds are better."""
    first = storm_day(pd.Series([pd.Timestamp(f"{year - 1}-12-31")]))[0]
    day = (storm_day(pred.block_start) - first).dt.days.to_numpy()
    counts, _ = day_weights(np.arange(day.max() + 1))
    y = pred.y.to_numpy()
    mean = {a: pred[[f"{a}|seed{s}" for s in seeds]].mean(axis=1).to_numpy() for a in (NETWORK, XGB, BLEND)}
    boot = {a: pr_auc_resamples(y, p, day, counts) for a, p in mean.items()}
    rows = []
    for a in (NETWORK, XGB, BLEND):
        r = {"year": year, "arm": a, "pr_auc": float(average_precision_score(y, mean[a]))}
        r["pr_auc_lo"], r["pr_auc_hi"] = interval(boot[a])
        r |= {f"pr_auc_seed{s}": float(average_precision_score(y, pred[f"{a}|seed{s}"])) for s in seeds}
        if a != XGB:
            r["gain"] = r["pr_auc"] / float(average_precision_score(y, mean[XGB])) - 1
            r["gain_lo"], r["gain_hi"] = interval(boot[a] / boot[XGB] - 1)
            r["better_share"] = float(np.mean(boot[a] > boot[XGB]))
            r["seeds_better"] = int(sum(r[f"pr_auc_seed{s}"] > float(average_precision_score(
                y, pred[f"{XGB}|seed{s}"])) for s in seeds))
            r["kept"] = bool(r["gain_lo"] > 0 and r["seeds_better"] >= min(2, len(seeds)))
        rows.append(r)
    out = pd.DataFrame(rows)
    print(out.round(4).to_string(index=False), flush=True)
    return out


# ---------- stages ----------

def fit_stage(name, years, cols, seeds, epochs, val_year=None):
    """Prep, the networks and XGBoost on `years`; with val_year, each network's PR-AUC there after every epoch."""
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    train = ft.train_rows(years)
    print(f"training rows {years[0]}-{years[-1]}: {len(train):,}, {int(train.y.sum()):,} positives "
          f"({time.time() - t0:.0f}s)", flush=True)
    prep = Prep().fit(train, cols)
    num, cats = prep.transform(train)
    y, w = train.y.to_numpy(), train.weight.to_numpy()
    base = float(np.sum(w * y) / np.sum(w))
    xgbs = {s: fit_xgb(train, cols, s, folder / f"xgb_seed{s}.json") for s in seeds}
    print(f"fitted XGBoost ({time.time() - t0:.0f}s)", flush=True)
    del train
    val = validation_sample(val_year, cols, prep) if val_year else None
    nets, curves = {}, {}
    for s in seeds:
        path = folder / f"net_seed{s}.pt"
        net, curves[s] = train_net(num, cats, y, w, s, epochs, prep.sizes, base, val, checkpoints=folder)
        torch.save(net.state_dict(), path)
        nets[s] = net
    return prep, nets, xgbs, curves


def select():
    cols, seeds = features(), list(SEEDS)
    prep, nets, xgbs, curves = fit_stage("select", [2020, 2021, 2022, 2023], cols, seeds, MAX_EPOCHS, val_year=2024)
    ep = pd.DataFrame(curves).rename_axis("epoch").reset_index()
    ep["epoch"] += 1
    ep.columns = ["epoch"] + [f"seed{s}" for s in seeds]
    ep["mean"] = ep[[f"seed{s}" for s in seeds]].mean(axis=1)
    best = int(ep.loc[ep["mean"].idxmax(), "epoch"])
    ep.to_csv(RESULTS / "nn_2024_epochs.csv", index=False)
    (OUT / "chosen_epochs.json").write_text(json.dumps({"epochs": best, "of": MAX_EPOCHS}))
    print(f"chosen: {best} of {MAX_EPOCHS} epochs (mean 2024 PR-AUC {ep['mean'].max():.4f})", flush=True)
    for s, net in nets.items():                       # each network as it stood after the chosen epoch
        net.load_state_dict(torch.load(OUT / "select" / f"net_seed{s}_epoch{best}.pt"))
    pred = add_blend(score_year(2024, cols, prep, nets, xgbs), seeds)
    pred.to_parquet(OUT / "pred_2024.parquet", index=False)
    judge(pred, seeds, 2024).to_csv(RESULTS / "nn_2024.csv", index=False)


def test():
    cols, seeds = features(), list(SEEDS)
    best = json.loads((OUT / "chosen_epochs.json").read_text())["epochs"]
    prep, nets, xgbs, _ = fit_stage("test", [2020, 2021, 2022, 2023, 2024], cols, seeds, best)
    pred = add_blend(score_year(ft.TEST_YEAR, cols, prep, nets, xgbs), seeds)
    pred.to_parquet(OUT / "pred_2025.parquet", index=False)
    judge(pred, seeds, ft.TEST_YEAR).assign(epochs=best).to_csv(RESULTS / "nn_2025.csv", index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["select", "test"])
    parser.add_argument("--smoke", action="store_true", help="two states, 2 epochs, 5 trees (data/smoke/root)")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"device {DEVICE}; {len(features())} inputs; root {data.ROOT}", flush=True)
    select() if args.stage == "select" else test()


if __name__ == "__main__":
    main()
