"""Graph networks over neighbouring counties (docs/experiments.md, E57b).

The hand-made neighbour inputs (strongest gust, CAPE, rain, worst outage, warning share within 100 km and upwind)
are replaced by a learned summary of every neighbour's state at the decision hour. Four kinds of graph layer are
compared with no neighbours at all, with E57a's network on the hand-made inputs, and with E55's XGBoost.

The graph
  links      each county to its neighbours within 100 km and its upwind counties within 200 km
             (intermediate.int_study__region_neighbors); edge inputs: distance / 100 km, sin and cos of the bearing,
             near and upwind flags
  messages   every neighbour's GRID inputs at the decision hour, read from an hour x county array built from
             marts.mart_study__region_1h for every county (not only the sampled rows): known-by-then, like the
             hand-made inputs. Heavy-tailed inputs log1p-scaled; all standardised on the training years; a missing
             value is 0 plus a flag

The network (E57a's, with the neighbour summary joined in)
  own inputs   E57a's Prep (rank -> normal, missing flags, embeddings) on its 110 inputs minus the 10 hand-made
               neighbour inputs, into 512-256 (LayerNorm, SiLU, dropout 0.2)
  neighbours   per arm (below) a 64-number summary; joined to the trunk, then 128, then one log-odds
  arms         none        no summary
               mean        GraphSAGE-mean: message = MLP(neighbour inputs, edge), averaged
               max-pool    GraphSAGE-pool: the same messages, element-wise max
               attention   GATv2 with edge inputs, 4 heads: messages weighted by softmax(a . LeakyReLU(W [own, msg]))
               gated       GatedGCN-style: messages scaled by sigmoid(W [own, msg]) and summed / sqrt(links)

  select  trained on 2020-2023; epochs per arm picked on the 2024 sample (every outage, 10% of the rest), as E57a;
          every 2024 decision scored with the newest HRRR run; each arm judged against none, against E57a's
          network (hand-made neighbours) and against E55's XGBoost (E57a's cached chances on the same rows)
  test    only if a graph arm beats the hand-made network on 2024: refitted on 2020-2024, scored once on 2025

Usage: STORM_ROOT=<main checkout> pixi run -e nn python -m ml.gnn_counties select [--arms ...] | test [--smoke]
  test   reads ml/results/gnn_2024.csv and chosen_epochs.json; models under <STORM_ROOT>/data/cache/gnn/test/
Writes ml/results/gnn_2024.csv (+ gnn_2024_epochs.csv), gnn_2025.csv; grid, models and chances under
<STORM_ROOT>/data/cache/gnn/ (a stopped run reuses fitted models).
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

import duckdb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
from sklearn.metrics import average_precision_score  # noqa: E402
from torch import nn  # noqa: E402

from ml import data  # noqa: E402
from ml import forecast_test as ft  # noqa: E402
from ml import nn_tabular as nt  # noqa: E402
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day  # noqa: E402

SEEDS = range(1 if data.SMOKE else 3)
MAX_EPOCHS = 1 if data.SMOKE else 6
BATCH, LR, WEIGHT_DECAY, DROPOUT, COUNTY_DROP = 8192, 1e-3, 1e-4, 0.2, 0.1
ARMS = ["none", "mean", "max-pool", "attention", "gated"]
GRID = ["gust_max_ms", "wind10_max_ms", "wind850_max_ms", "shear_0_6km_max_ms", "cape_max_jkg", "precip_sum_mm",
        "precip_max_1h_mm", "pct_out_now", "max_pct_out_prev_24h", "warn_svr", "warn_tor", "warn_wind",
        "spc_wind_prob", "spc_tor_prob"]
LOG = {"cape_max_jkg", "precip_sum_mm", "precip_max_1h_mm", "pct_out_now", "max_pct_out_prev_24h"}
EPOCH0 = pd.Timestamp("2018-01-01")
OUT = data.ROOT / "data" / "cache" / "gnn"
RESULTS = Path(__file__).resolve().parent / "results"
DEVICE = nt.DEVICE
XGB, HANDMADE = "E55 XGBoost", "E57a network (hand-made neighbours)"


def own_features():
    """E57a's inputs without the hand-made neighbour ones."""
    return [c for c in nt.features() if not c.startswith(("near_", "up_"))]


# ---------- the graph and the hour x county grid ----------

class Graph:
    """Counties, their links (padded to the most links any county has) and edge inputs."""

    def __init__(self, db=data.DB):
        con = duckdb.connect(str(db), read_only=True)
        self.regions = [r[0] for r in con.sql(
            "SELECT DISTINCT region_fips FROM marts.mart_study__region_1h ORDER BY 1").fetchall()]
        pairs = con.sql("SELECT * FROM intermediate.int_study__region_neighbors WHERE is_near OR is_upwind").df()
        con.close()
        self.index = {r: i for i, r in enumerate(self.regions)}
        pairs = pairs[pairs.region_fips.isin(self.index) & pairs.neighbor_fips.isin(self.index)]
        k = int(pairs.groupby("region_fips").size().max())
        n = len(self.regions)
        self.nbr = np.full((n, k), -1, np.int64)
        self.edge = np.zeros((n, k, 5), np.float32)
        for r, g in pairs.groupby("region_fips"):
            i, m = self.index[r], len(g)
            self.nbr[i, :m] = g.neighbor_fips.map(self.index).to_numpy()
            b = np.radians(g.bearing_deg.to_numpy())
            self.edge[i, :m] = np.column_stack([g.distance_km.to_numpy() / 100, np.sin(b), np.cos(b),
                                                g.is_near.to_numpy(), g.is_upwind.to_numpy()])
        print(f"graph: {n:,} counties, {len(pairs):,} links, up to {k} per county", flush=True)


def grid_path():
    return OUT / "grid.npy"


def build_grid(graph, db=data.DB):
    """[hour since 2018-01-01, county, GRID input] float16 on disk, raw values (NaN = missing)."""
    path = grid_path()
    meta = OUT / "grid.json"
    stamp = {"warehouse_mtime": Path(db).stat().st_mtime, "grid": GRID, "regions": len(graph.regions)}
    if path.exists() and meta.exists() and json.loads(meta.read_text()) == stamp:
        return np.load(path, mmap_mode="r")
    con = duckdb.connect(str(db), read_only=True)
    last = con.sql("SELECT max(hour) FROM marts.mart_study__region_1h").fetchall()[0][0]
    hours = int((pd.Timestamp(last) - EPOCH0) / pd.Timedelta(hours=1)) + 1
    OUT.mkdir(parents=True, exist_ok=True)
    arr = np.lib.format.open_memmap(path, mode="w+", dtype=np.float16, shape=(hours, len(graph.regions), len(GRID)))
    arr[:] = np.nan
    cols = ", ".join(f"{c}::DOUBLE AS {c}" for c in GRID)
    for year in range(EPOCH0.year, pd.Timestamp(last).year + 1):
        df = con.sql(f"SELECT region_fips, hour, {cols} FROM marts.mart_study__region_1h "
                     f"WHERE year(hour) = {year}").df()
        h = ((df.hour - EPOCH0) / pd.Timedelta(hours=1)).astype(np.int64).to_numpy()
        r = df.region_fips.map(graph.index).to_numpy()
        arr[h, r] = df[GRID].to_numpy(np.float32).astype(np.float16)
        print(f"grid {year}: {len(df):,} county-hours", flush=True)
    arr.flush()
    con.close()
    meta.write_text(json.dumps(stamp))
    return np.load(path, mmap_mode="r")


class GridScale:
    """log1p for heavy tails, then mean / std from the training years; missing -> 0 plus a flag."""

    def fit(self, grid, years, rng=None):
        rng = rng or np.random.default_rng(0)
        lo = hour_index(pd.Timestamp(f"{years[0]}-01-01"))
        hi = hour_index(pd.Timestamp(f"{years[-1] + 1}-01-01"))
        sample = np.asarray(grid[np.sort(rng.integers(lo, hi, 2000))], np.float32).reshape(-1, len(GRID))
        sample = self._log(sample)
        self.mean = np.nanmean(sample, axis=0)
        self.std = np.nanstd(sample, axis=0) + 1e-6
        return self

    @staticmethod
    def _log(x):
        x = x.copy()
        for i, c in enumerate(GRID):
            if c in LOG:
                x[..., i] = np.log1p(np.clip(x[..., i], 0, None))
        return x

    def values(self, x):
        """x: [..., len(GRID)] -> scaled values, NaN kept."""
        return ((self._log(np.asarray(x, np.float32)) - self.mean) / self.std).astype(np.float32)

    def __call__(self, x):
        """x: [..., len(GRID)] float -> [..., 2 * len(GRID)] (scaled values, missing flags)."""
        x = self.values(x)
        miss = np.isnan(x)
        return np.concatenate([np.where(miss, 0, x), miss], axis=-1).astype(np.float32)


def hour_index(ts):
    """Hours since EPOCH0: an int for one timestamp, an int64 array for many."""
    if isinstance(ts, pd.Timestamp):
        return int((ts - EPOCH0) / pd.Timedelta(hours=1))
    return ((pd.to_datetime(pd.Series(ts)) - EPOCH0) / pd.Timedelta(hours=1)).to_numpy().astype(np.int64)


class DeviceGrid:
    """The scaled grid for hours [h0, h1) on the GPU (float16), with the graph's links and edge inputs, so a batch's
    neighbours are gathered there instead of on the CPU."""

    def __init__(self, grid, scale, graph, h0, h1, chunk=2000):
        self.h0 = h0
        parts = []
        for i in range(h0, h1, chunk):
            parts.append(torch.from_numpy(scale.values(grid[i:min(i + chunk, h1)])).to(DEVICE, torch.float16))
        self.values = torch.cat(parts)                                     # [hours, counties, F], NaN = missing
        self.nbr = torch.from_numpy(graph.nbr).to(DEVICE)
        self.edge = torch.from_numpy(graph.edge).to(DEVICE)
        print(f"grid on {DEVICE}: hours {h0:,}-{h1:,}, {self.values.numel() * 2 / 1e9:.1f} GB", flush=True)

    def gather(self, regions, hours):
        """regions, hours: int64 tensors [n] -> neighbour inputs [n, K, 2F + 5] (float32), mask [n, K]."""
        nbr = self.nbr[regions]
        mask = nbr >= 0
        x = self.values[(hours - self.h0)[:, None], nbr.clamp(min=0)].float()
        miss = torch.isnan(x)
        x = torch.cat([torch.nan_to_num(x, nan=0.0), miss.float()], dim=-1) * mask.unsqueeze(-1)
        return torch.cat([x, self.edge[regions]], dim=-1), mask


def neighbour_inputs(grid, scale, graph, regions, hours):
    """For rows (region index, hour index): neighbour inputs [n, K, 2F + 5] and mask [n, K]."""
    nbr = graph.nbr[regions]                                     # [n, K]
    mask = nbr >= 0
    vals = np.asarray(grid[hours[:, None], np.where(mask, nbr, 0)], np.float32)
    x = scale(vals)
    x[~mask] = 0
    return np.concatenate([x, graph.edge[regions]], axis=-1), mask


# ---------- the network ----------

class Summary(nn.Module):
    """A 64-number summary of a county's neighbours; `kind` is the arm."""

    def __init__(self, kind, d_in, d_own, d=64, heads=4):
        super().__init__()
        self.kind, self.heads = kind, heads
        self.msg = nn.Sequential(nn.Linear(d_in, d), nn.SiLU(), nn.Linear(d, d))
        # a linear layer on [own, message] written as own-part + message-part, so the county's own state is never
        # copied to every link (same function, far less GPU memory)
        if kind == "attention":
            self.att_own, self.att_msg = nn.Linear(d_own, d), nn.Linear(d, d, bias=False)
            self.att_a = nn.Parameter(torch.randn(heads, d // heads) * 0.1)
        if kind == "gated":
            self.gate_own, self.gate_msg = nn.Linear(d_own, d), nn.Linear(d, d, bias=False)
        self.norm = nn.LayerNorm(d)

    def forward(self, own, nb, mask):
        m = self.msg(nb)                                         # [B, K, d]
        maskf = mask.unsqueeze(-1).float()
        count = maskf.sum(1).clamp(min=1)
        if self.kind == "mean":
            out = (m * maskf).sum(1) / count
        elif self.kind == "max-pool":
            out = m.masked_fill(~mask.unsqueeze(-1), -1e4).amax(1)
            out = torch.where(mask.any(1, keepdim=True), out, torch.zeros_like(out))
        elif self.kind == "attention":
            b, k, d = m.shape
            z = self.att_own(own).unsqueeze(1) + self.att_msg(m)
            e = nn.functional.leaky_relu(z, 0.2).view(b, k, self.heads, d // self.heads)
            score = (e * self.att_a).sum(-1).masked_fill(~mask.unsqueeze(-1), -1e4)     # [B, K, H]
            alpha = torch.softmax(score, dim=1) * mask.unsqueeze(-1)
            out = (alpha.unsqueeze(-1) * m.view(b, k, self.heads, d // self.heads)).sum(1).reshape(b, d)
        else:                                                    # gated
            g = torch.sigmoid(self.gate_own(own).unsqueeze(1) + self.gate_msg(m))
            out = (g * m * maskf).sum(1) / count.sqrt()
        return self.norm(out)


class GraphNet(nn.Module):
    def __init__(self, kind, n_num, n_county, n_state, d_nb):
        super().__init__()
        self.kind = kind
        self.emb = nn.ModuleList([nn.Embedding(12, 4), nn.Embedding(24, 6), nn.Embedding(8, 4),
                                  nn.Embedding(n_state, 8), nn.Embedding(n_county, 16)])
        width = n_num + 4 + 6 + 4 + 8 + 16
        self.trunk = nn.Sequential(nn.Linear(width, 512), nn.LayerNorm(512), nn.SiLU(), nn.Dropout(DROPOUT),
                                   nn.Linear(512, 256), nn.LayerNorm(256), nn.SiLU(), nn.Dropout(DROPOUT))
        self.summary = None if kind == "none" else Summary(kind, d_nb, 256)
        self.top = nn.Sequential(nn.Linear(256 + (0 if kind == "none" else 64), 128), nn.LayerNorm(128), nn.SiLU(),
                                 nn.Dropout(DROPOUT))
        self.head = nn.Linear(128, 1)

    def forward(self, num, cats, nb=None, mask=None):
        h = self.trunk(torch.cat([num] + [e(cats[:, i]) for i, e in enumerate(self.emb)], dim=1))
        if self.summary is not None:
            h = torch.cat([h, self.summary(h, nb, mask)], dim=1)
        return self.head(self.top(h)).squeeze(1)


# ---------- inputs for a set of rows ----------

class Rows:
    """Transformed rows: own inputs, categories, region and hour indices (neighbours are read per batch)."""

    def __init__(self, df, prep, graph):
        self.num, self.cats = prep.transform(df)
        self.region = df.region_fips.astype(str).map(graph.index).fillna(-1).astype(np.int64).to_numpy()
        self.hour = hour_index(df.block_start)
        self.y = df.y.to_numpy().astype(np.float32) if "y" in df else None
        self.w = df.weight.to_numpy().astype(np.float32) if "weight" in df else None

    def __len__(self):
        return len(self.num)

    def batch(self, idx, grid, scale, graph, kind):
        num = torch.from_numpy(self.num[idx]).to(DEVICE, non_blocking=True)
        cats = torch.from_numpy(self.cats[idx]).to(DEVICE, non_blocking=True)
        if kind == "none":
            return num, cats, None, None
        reg = self.region[idx]
        if isinstance(grid, DeviceGrid):
            r = torch.from_numpy(np.where(reg >= 0, reg, 0)).to(DEVICE)
            nb, mask = grid.gather(r, torch.from_numpy(self.hour[idx]).to(DEVICE))
            return num, cats, nb, mask & torch.from_numpy(reg >= 0).to(DEVICE)[:, None]
        nb, mask = neighbour_inputs(grid, scale, graph, np.where(reg >= 0, reg, 0), self.hour[idx])
        mask &= (reg >= 0)[:, None]
        return num, cats, torch.from_numpy(nb).to(DEVICE), torch.from_numpy(mask).to(DEVICE)


def predict(net, rows, grid, scale, graph, step=32_768):
    net.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(rows), step):
            idx = np.arange(i, min(i + step, len(rows)))
            out.append(torch.sigmoid(net(*rows.batch(idx, grid, scale, graph, net.kind))).float().cpu().numpy())
    return np.concatenate(out) if out else np.zeros(0, np.float32)


def train(kind, rows, sizes, base, grid, scale, graph, seed, epochs, val=None, folder=None):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    d_nb = 2 * len(GRID) + 5
    net = GraphNet(kind, d_nb=d_nb, **sizes).to(DEVICE)
    with torch.no_grad():
        net.head.bias.fill_(float(np.log(base / (1 - base))))
    opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=MAX_EPOCHS * -(-len(rows) // BATCH))
    loss_fn = nn.BCEWithLogitsLoss(reduction="none")
    y_t, w_t = torch.from_numpy(rows.y), torch.from_numpy(rows.w)
    scores = []
    for epoch in range(epochs):
        net.train()
        t0 = time.time()
        perm = rng.permutation(len(rows))
        for i in range(0, len(rows), BATCH):
            idx = perm[i:i + BATCH]
            num, cats, nb, mask = rows.batch(idx, grid, scale, graph, kind)
            drop = torch.rand(len(idx), device=DEVICE) < COUNTY_DROP
            cats[:, 4] = torch.where(drop, torch.zeros_like(cats[:, 4]), cats[:, 4])
            yb, wb = y_t[idx].to(DEVICE), w_t[idx].to(DEVICE)
            loss = (loss_fn(net(num, cats, nb, mask), yb) * wb).sum() / wb.sum()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            sched.step()
        if folder is not None:
            torch.save(net.state_dict(), folder / f"{kind}_seed{seed}_epoch{epoch + 1}.pt")
        if val is not None:
            p = predict(net, val, grid, scale, graph)
            scores.append(float(average_precision_score(val.y, p, sample_weight=val.w)))
            print(f"{kind} seed {seed} epoch {epoch + 1}: 2024 sample PR-AUC {scores[-1]:.4f} "
                  f"({time.time() - t0:.0f}s)", flush=True)
    return net, scores


# ---------- scoring a year ----------

def score_year(year, cols, prep, nets, grid, scale, graph):
    """Each arm and seed's chance for every decision of `year` (window weather averaged over the HRRR versions).
    Each state's rows are transformed once per version and shared by every model."""
    parts = []
    for rows, versions in nt.scored_rows(year):
        out = rows[["region_fips", "block_start", "y"]].copy()
        keys = rows[["region_fips", "block_start"]].reset_index(drop=True)
        sums = {k: np.zeros(len(rows)) for k in nets}
        for v in versions:
            x = ft.with_version(rows, cols, v).reset_index(drop=True).assign(
                region_fips=keys.region_fips, block_start=keys.block_start)
            r = Rows(x, prep, graph)
            for k, net in nets.items():
                sums[k] += predict(net, r, grid, scale, graph)
        for (kind, s), total in sums.items():
            out[f"{kind}|seed{s}"] = total / len(versions)
        parts.append(out)
        print(f"{year}: {len(out):,} decisions scored", flush=True)
    return pd.concat(parts, ignore_index=True)


def judge(pred, arms, seeds, year, references):
    """E55's rule for each arm against each reference."""
    first = storm_day(pd.Series([pd.Timestamp(f"{year - 1}-12-31")]))[0]
    day = (storm_day(pred.block_start) - first).dt.days.to_numpy()
    counts, _ = day_weights(np.arange(day.max() + 1))
    y = pred.y.to_numpy()
    every = list(dict.fromkeys(arms + references))
    mean = {a: pred[[f"{a}|seed{s}" for s in seeds]].mean(axis=1).to_numpy() for a in every}
    score = {a: float(average_precision_score(y, p)) for a, p in mean.items()}
    seed_score = {(a, s): float(average_precision_score(y, pred[f"{a}|seed{s}"])) for a in every for s in seeds}
    boot = {a: pr_auc_resamples(y, p, day, counts) for a, p in mean.items()}
    rows = []
    for a in every:
        r = {"year": year, "arm": a, "pr_auc": score[a]}
        r["pr_auc_lo"], r["pr_auc_hi"] = interval(boot[a])
        r |= {f"pr_auc_seed{s}": seed_score[(a, s)] for s in seeds}
        for ref in references:
            if ref == a:
                continue
            tag = {"none": "vs_none", HANDMADE: "vs_handmade", XGB: "vs_xgb"}.get(ref, f"vs_{ref}")
            r[f"{tag}_gain"] = score[a] / score[ref] - 1
            r[f"{tag}_lo"], r[f"{tag}_hi"] = interval(boot[a] / boot[ref] - 1)
            r[f"{tag}_seeds_better"] = int(sum(seed_score[(a, s)] > seed_score[(ref, s)] for s in seeds))
            r[f"{tag}_kept"] = bool(r[f"{tag}_lo"] > 0 and r[f"{tag}_seeds_better"] >= min(2, len(seeds)))
        rows.append(r)
    out = pd.DataFrame(rows)
    show = ["arm", "pr_auc"] + [c for c in out.columns if c.endswith(("_gain", "_kept"))]
    print(out[show].round(4).to_string(index=False), flush=True)
    return out


# ---------- stages ----------

def device_grid(raw, scale, graph, first, last):
    """The grid for years first..last on the GPU (the numpy memmap on a CPU)."""
    if DEVICE != "cuda":
        return raw
    return DeviceGrid(raw, scale, graph, hour_index(pd.Timestamp(f"{first}-01-01")),
                      min(len(raw), hour_index(pd.Timestamp(f"{last + 1}-01-01"))))


def setup(years, extra=1):
    """extra: years after the training years kept on the GPU too (select: 2024 for validation and scoring)."""
    graph = Graph()
    raw = build_grid(graph)
    scale = GridScale().fit(raw, years)
    grid = device_grid(raw, scale, graph, years[0], years[-1] + extra)
    cols = own_features()
    t0 = time.time()
    train_df = ft.train_rows(years)
    print(f"training rows {years[0]}-{years[-1]}: {len(train_df):,}, {int(train_df.y.sum()):,} positives "
          f"({time.time() - t0:.0f}s)", flush=True)
    prep = nt.Prep().fit(train_df, cols)
    rows = Rows(train_df, prep, graph)
    base = float(np.sum(rows.w * rows.y) / np.sum(rows.w))
    del train_df
    return graph, grid, scale, cols, prep, rows, base


def validation_rows(year, cols, prep, graph, rng=None):
    rng = rng or np.random.default_rng(0)
    parts = []
    for rows, versions in nt.scored_rows(year):
        keep = (rows.y.to_numpy() == 1) | (rng.random(len(rows)) < nt.VAL_NEG)
        v = ft.with_version(rows[keep], cols, versions[0]).reset_index(drop=True)
        v = v.assign(region_fips=rows.region_fips[keep].to_numpy(), block_start=rows.block_start[keep].to_numpy(),
                     y=rows.y[keep].to_numpy(), weight=np.where(rows.y.to_numpy()[keep] == 1, 1.0, 1 / nt.VAL_NEG))
        parts.append(v)
    return Rows(pd.concat(parts, ignore_index=True), prep, graph)


def select(arms):
    seeds, years = list(SEEDS), [2020, 2021, 2022, 2023]
    folder = OUT / "select"
    folder.mkdir(parents=True, exist_ok=True)
    graph, grid, scale, cols, prep, rows, base = setup(years)
    val = validation_rows(2024, cols, prep, graph)
    print(f"2024 sample: {len(val):,} rows", flush=True)
    curves_path = RESULTS / ("gnn_2024_epochs_smoke.csv" if data.SMOKE else "gnn_2024_epochs.csv")
    curves = (pd.read_csv(curves_path) if curves_path.exists()
              else pd.DataFrame(columns=["arm", "seed", "epoch", "pr_auc"]))
    nets = {}
    for kind in arms:
        for s in seeds:
            done = curves[(curves.arm == kind) & (curves.seed == s)]
            if len(done) == MAX_EPOCHS and (folder / f"{kind}_seed{s}_epoch{MAX_EPOCHS}.pt").exists():
                print(f"{kind} seed {s}: already trained", flush=True)
                continue
            _, sc = train(kind, rows, prep.sizes, base, grid, scale, graph, s, MAX_EPOCHS, val, folder)
            curves = pd.concat([curves[~((curves.arm == kind) & (curves.seed == s))], pd.DataFrame(
                {"arm": kind, "seed": s, "epoch": range(1, MAX_EPOCHS + 1), "pr_auc": sc})], ignore_index=True)
            curves.to_csv(curves_path, index=False)
    chosen = {}
    for kind in arms:
        c = curves[curves.arm == kind].groupby("epoch").pr_auc.mean()
        chosen[kind] = int(c.idxmax())
        print(f"{kind}: {chosen[kind]} of {MAX_EPOCHS} epochs (2024 sample PR-AUC {c.max():.4f})", flush=True)
        for s in seeds:
            net = GraphNet(kind, d_nb=2 * len(GRID) + 5, **prep.sizes).to(DEVICE)
            net.load_state_dict(torch.load(folder / f"{kind}_seed{s}_epoch{chosen[kind]}.pt"))
            nets[(kind, s)] = net
    (OUT / "chosen_epochs.json").write_text(json.dumps(chosen))
    del rows, val
    pred = score_year(2024, cols, prep, nets, grid, scale, graph)
    if not data.SMOKE:                 # E57a's chances (network on hand-made inputs, E55 XGBoost), same decisions
        old = pd.read_parquet(nt.OUT / "pred_2024.parquet").rename(
            columns=lambda c: c.replace("network|", f"{HANDMADE}|") if c.startswith("network|") else c)
        keep = ["region_fips", "block_start"] + [c for c in old.columns if c.startswith((HANDMADE, XGB))]
        pred = pred.merge(old[keep], on=["region_fips", "block_start"], how="inner", validate="1:1")
        refs = ["none", HANDMADE, XGB]
    else:
        refs = ["none"]
    graph_arms = [a for a in arms if a != "none"]
    if not data.SMOKE and graph_arms:
        best = max(graph_arms, key=lambda a: average_precision_score(
            pred.y, pred[[f"{a}|seed{s}" for s in seeds]].mean(axis=1)))
        blend = f"{best} + XGBoost"
        for s in seeds:
            pred[f"{blend}|seed{s}"] = (pred[f"{best}|seed{s}"] + pred[f"{XGB}|seed{s}"]) / 2
        arms = arms + [blend]
    pred.to_parquet(OUT / "pred_2024.parquet", index=False)
    judge(pred, arms, seeds, 2024, refs).to_csv(RESULTS / ("gnn_2024_smoke.csv" if data.SMOKE else "gnn_2024.csv"),
                                                 index=False)


def test():
    """The plan's last step: the arms that beat the hand-made network on 2024 (plus none, and 2024's average with
    XGBoost), refitted on 2020-2024 for the epochs chosen on 2024 and scored once on every 2025 decision with the
    five-run mean. References: E57a's network and E55's XGBoost, refitted the same way (E57a's cached 2025 chances)."""
    seeds, years = list(SEEDS), [2020, 2021, 2022, 2023, 2024]
    chosen = json.loads((OUT / "chosen_epochs.json").read_text())
    if data.SMOKE:
        arms, blend = list(chosen), None
    else:
        sel = pd.read_csv(RESULTS / "gnn_2024.csv")
        kept = sel[sel.vs_handmade_kept.fillna(False).astype(bool)].arm.tolist()
        blend = next((a for a in kept if a.endswith(" + XGBoost")), None)
        arms = ["none"] + [a for a in kept if a in ARMS and a != "none"]
        if len(arms) == 1:
            print("no graph arm beat the hand-made network on 2024: nothing to test", flush=True)
            return
    print(f"testing {arms}" + (f" and {blend}" if blend else "") + f"; epochs {chosen}", flush=True)
    folder = OUT / "test"
    folder.mkdir(parents=True, exist_ok=True)
    graph, grid, scale, cols, prep, rows, base = setup(years, extra=0)      # 2020-2024 on the GPU for training
    nets = {}
    for kind in arms:
        for s in seeds:
            net = GraphNet(kind, d_nb=2 * len(GRID) + 5, **prep.sizes).to(DEVICE)
            path = folder / f"{kind}_seed{s}_epoch{chosen[kind]}.pt"
            if path.exists():
                print(f"{kind} seed {s}: already trained", flush=True)
                net.load_state_dict(torch.load(path))
            else:
                t0 = time.time()
                net, _ = train(kind, rows, prep.sizes, base, grid, scale, graph, s, chosen[kind], folder=folder)
                print(f"{kind} seed {s}: {chosen[kind]} epochs ({time.time() - t0:.0f}s)", flush=True)
            nets[(kind, s)] = net
    del rows, grid
    if DEVICE == "cuda":
        torch.cuda.empty_cache()
    grid = device_grid(build_grid(graph), scale, graph, ft.TEST_YEAR, ft.TEST_YEAR)    # 2025 only, for scoring
    pred = score_year(ft.TEST_YEAR, cols, prep, nets, grid, scale, graph)
    refs = ["none"]
    if not data.SMOKE:
        old = pd.read_parquet(nt.OUT / "pred_2025.parquet").rename(
            columns=lambda c: c.replace("network|", f"{HANDMADE}|") if c.startswith("network|") else c)
        keep = ["region_fips", "block_start"] + [c for c in old.columns if c.startswith((HANDMADE, XGB))]
        n = len(pred)
        pred = pred.merge(old[keep], on=["region_fips", "block_start"], how="inner", validate="1:1")
        print(f"2025: {len(pred):,} of {n:,} decisions also scored by E57a", flush=True)
        refs = ["none", HANDMADE, XGB]
        if blend:
            best = blend.removesuffix(" + XGBoost")
            for s in seeds:
                pred[f"{blend}|seed{s}"] = (pred[f"{best}|seed{s}"] + pred[f"{XGB}|seed{s}"]) / 2
            arms = arms + [blend]
    pred.to_parquet(OUT / "pred_2025.parquet", index=False)
    out = judge(pred, arms, seeds, ft.TEST_YEAR, refs)
    out["epochs"] = out.arm.map(lambda a: chosen.get(a.removesuffix(" + XGBoost")))
    out.to_csv(RESULTS / ("gnn_2025_smoke.csv" if data.SMOKE else "gnn_2025.csv"), index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["select", "test"])
    parser.add_argument("--arms", nargs="+", choices=ARMS, default=ARMS)
    parser.add_argument("--smoke", action="store_true", help="two states, 1 epoch, 1 seed (data/smoke/root)")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"device {DEVICE}; {len(own_features())} own inputs, {len(GRID)} neighbour inputs; root {data.ROOT}",
          flush=True)
    arms = args.arms if "none" in args.arms else ["none"] + args.arms
    select(arms) if args.stage == "select" else test()


if __name__ == "__main__":
    main()
