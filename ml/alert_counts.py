"""What a county alert would have looked like in 2025, for choosing the alert cut-off (docs/alerts.md).

The held-out USA live model (trained on 2020-2024, fed the five HRRR runs; ml/train_live_usa.py) on every 2025
county-hour. An alert starts when a county's chance reaches the cut-off and lasts while it stays there; hours above
the cut-off less than MERGE_H apart are one alert (a person is told once per storm, not every hour).

Per cut-off and area:
  alerts per county-year   mean, median county, 90th-percentile county
  alerts followed by an outage   an alert is a hit when a new outage starts in the window of any of its hours
  outages alerted    a new outage (a run of hours whose window holds it) is alerted when any of those hours is above
  warning            hours from the alert's start to the outage's start (median, for alerted outages)
and the same for warnings + outlook at the same number of alert hours in the area.

The cut-off is a chance, so it belongs to one model: for a new model, read its level off its own held-out year at the
same alerts per county-year (`level_for_rate`).

Usage: pixi run python -m ml.alert_counts
Writes ml/results/alert_counts_2025.csv.
"""
import duckdb
import numpy as np
import pandas as pd

from ml import data

PRED = data.ROOT / "data" / "cache" / "live_usa" / "pred_2025.parquet"
DECISIONS = data.ROOT / "data" / "explore" / "decisions_2025.parquet"
OUT = data.ROOT / "ml" / "results" / "alert_counts_2025.csv"
CUTOFFS = [0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30]
MERGE_H = 6                     # above-cut-off hours closer than this are one alert
LEAD_H = 2                      # the window starts 2 h after the decision
AREAS = {"USA": None, "MO + IL": ("17", "29")}


def load():
    con = duckdb.connect()
    df = con.sql(f"""
        SELECT p.region_fips, p.block_start, p.y, p.held_out AS p_model, d.p_official
        FROM '{PRED}' p JOIN '{DECISIONS}' d USING (region_fips, block_start)
        ORDER BY region_fips, block_start""").df()
    con.close()
    df["region_fips"] = df.region_fips.astype(str)
    df["t"] = (df.block_start - pd.Timestamp("2025-01-01")) // pd.Timedelta(hours=1)
    return df


def runs(fips, t, gap):
    """Run ids for sorted (fips, t) rows: a new run when the county changes or the hours are more than `gap` apart."""
    if len(t) == 0:
        return np.zeros(0, dtype=int)
    new = np.r_[True, (fips[1:] != fips[:-1]) | (np.diff(t) > gap)]
    return np.cumsum(new) - 1


def alerts(df, score, cut):
    """One row per alert (county, start, end, hit) and per outage (alerted, warning hours)."""
    fips, t, y = df.region_fips.to_numpy(), df.t.to_numpy(), df.y.to_numpy()
    above = df[score].to_numpy() >= cut

    a = np.flatnonzero(above)
    aid = runs(fips[a], t[a], MERGE_H)
    al = pd.DataFrame({"aid": aid, "fips": fips[a], "t": t[a], "y": y[a]}).groupby("aid").agg(
        fips=("fips", "first"), start=("t", "min"), hit=("y", "max"))

    o = np.flatnonzero(y == 1)
    oid = runs(fips[o], t[o], 1)
    ev = pd.DataFrame({"oid": oid, "t": t[o], "above": above[o], "row": o})
    onset = ev.groupby("oid").t.max() + LEAD_H          # the last decision whose window holds it, plus the lead
    first = ev[ev.above].groupby("oid").row.min()          # the first alerted hour of each alerted outage
    row_to_alert = pd.Series(aid, index=a)
    start = al.start.reindex(row_to_alert.reindex(first.to_numpy()).to_numpy()).to_numpy()
    warning = onset.reindex(first.index).to_numpy() - start
    return al, len(onset), warning


def summarize(df, score, cut, n_counties):
    al, n_out, warning = alerts(df, score, cut)
    per = al.groupby("fips").size().reindex(df.region_fips.unique(), fill_value=0)
    return {
        "alerts": len(al), "alerts_per_county_year": len(al) / n_counties,
        "median_county": float(per.median()), "p90_county": float(per.quantile(0.9)),
        "share_alerts_hit": al.hit.mean() if len(al) else np.nan,
        "outages": n_out, "share_outages_alerted": len(warning) / n_out,
        "median_warning_h": float(np.median(warning)) if len(warning) else np.nan,
        "alert_hours": int((df[score] >= cut).sum()),
    }


def level_for_rate(p, fips, t, rate, n_counties):
    """The cut-off that gives `rate` alerts per county-year on a model's held-out year (bisection on the chance)."""
    lo, hi = float(np.quantile(p, 0.5)), float(p.max())
    for _ in range(30):
        mid = (lo + hi) / 2
        a = np.flatnonzero(p >= mid)
        n = (runs(fips[a], t[a], MERGE_H).max() + 1 if len(a) else 0) / n_counties
        lo, hi = (mid, hi) if n > rate else (lo, mid)
    return hi


def main():
    df = load()
    print(f"{len(df):,} county-hours, {df.region_fips.nunique():,} counties", flush=True)
    rows = []
    for area, states in AREAS.items():
        part = df if states is None else df[df.region_fips.str[:2].isin(states)].reset_index(drop=True)
        n_c = part.region_fips.nunique()
        off = np.sort(part.p_official.to_numpy())[::-1]
        for cut in CUTOFFS:
            m = summarize(part, "p_model", cut, n_c)
            # warnings + outlook at the same number of alert hours (ties at the cut-off included)
            off_cut = off[min(m["alert_hours"], len(off)) - 1] if m["alert_hours"] else np.inf
            o = summarize(part, "p_official", off_cut, n_c)
            rows.append({"area": area, "counties": n_c, "cutoff": cut, **m,
                         **{f"official_{k}": v for k, v in o.items()}})
            r = rows[-1]
            print(f"{area:8} {cut:.2f}  {r['alerts_per_county_year']:5.1f}/county-yr  "
                  f"hit {r['share_alerts_hit']:.0%}  caught {r['share_outages_alerted']:.0%}  "
                  f"warn {r['median_warning_h']:.0f} h  | official: {r['official_alerts_per_county_year']:.1f}, "
                  f"hit {r['official_share_alerts_hit']:.0%}, caught {r['official_share_outages_alerted']:.0%}",
                  flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
