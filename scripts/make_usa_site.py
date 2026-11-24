"""Data for the USA site (site/usa/): the live county map, the county pages, the 2025 record and the storm replays.

  site/usa/data/map.json        county and state shapes (lon/lat, simplified), drawn with d3
  site/usa/data/counties.json   per county: name, state, time zone, customers, place facts as percentiles, flags
  site/usa/data/record.json     the alert rule replayed on 2025: nationally, by month, by state (the scorecard)
  site/usa/data/replays.json    five 2025 storms hour by hour: the model's chance, counties out, official warnings
  site/usa/data/zip.json        ZIP code -> county (Census 2020 ZCTA-county file, largest land share)
  site/usa/county/<id>.html     one page per county, with its 2025 alerts
  outlook_shapes.json           (--outlook DIR) projected county paths for storm-outage-live's outlook image

The 2025 numbers are the held-out USA live model (trained on 2020-2024, data/cache/live_usa/pred_2025.parquet, as
ml/alert_counts.py) at the live alert levels in storm-outage-live alerts/config.json (Elevated 0.10, High 0.20), so
the scorecard shows what the live feed would have sent. Warnings + outlook are compared at the same number of
alert-hours, as ml/alert_counts.py does.

Usage: pixi run python scripts/make_usa_site.py --zcta FILE [--outlook DIR]
  (run from the storm-outage-risk checkout on branch usa: it reads data/, live/static_usa/ and ml/)
"""
import argparse
import html
import json
import math
import sys
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

MAIN = Path.home() / "projects" / "storm-outage-risk"           # data/, live/, ml/ (branch usa)
SITE = Path(__file__).resolve().parent.parent / "site" / "usa"
sys.path.insert(0, str(MAIN))
from ml import alert_counts as ac  # noqa: E402
from ml.data import DB  # noqa: E402

PRED = MAIN / "data" / "cache" / "live_usa" / "pred_2025.parquet"
DECISIONS = MAIN / "data" / "explore" / "decisions_2025.parquet"
STATIC = MAIN / "live" / "static_usa"
COUNTIES_TZ = Path.home() / "projects" / "storm-outage-live" / "alerts" / "counties.json"
LEVELS = [("Elevated", 0.10), ("High", 0.20)]       # storm-outage-live alerts/config.json, model 2026-11-14T17:58Z
UNRELIABLE = 0.2        # hist_quiet_event_rate above this: "outages" (1%+) in more than 1 in 5 calm 6-hour periods
SIMPLIFY = 0.02
REPLAYS = [             # (id, title, first decision hour, last), UTC
    ("2025-03-14", "March 14–16: the mid-March outbreak", "2025-03-14T12", "2025-03-16T12"),
    ("2025-03-04", "March 4–5: a windstorm across the East", "2025-03-04T06", "2025-03-05T18"),
    ("2025-02-15", "February 15–17: wind, rain and ice", "2025-02-15T12", "2025-02-17T06"),
    ("2025-05-16", "May 16–17: tornadoes and wind, Plains to Appalachia", "2025-05-16T12", "2025-05-17T18"),
    ("2025-06-18", "June 18–20: the summer storms", "2025-06-18T12", "2025-06-20T06"),
]
FACTS = [   # (key, column, table, label, higher means)
    ("events", "hist_events_per_year", "history", "outages of 1%+ of customers a year", "more outages"),
    ("hours_out", "hist_hours_out_per_customer", "history", "hours without power per customer a year", "longer"),
    ("hit_rate", "hist_storm_hit_rate", "history", "stormy 6-hour periods with an outage of 1%+", "more often"),
    ("canopy", "canopy_mean_pct", "regions", "tree canopy (%)", "more trees"),
    ("treed_roads", "road_treed_share", "place", "share of roads under trees", "more"),
    ("old_homes", "share_homes_pre1960", "regions", "share of homes built before 1960", "older"),
    ("saidi", "util_saidi", "place", "utility outage minutes a year (SAIDI)", "longer"),
]


def ring_area(r):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(r, r[1:], strict=False)) / 2


def rounded(geom):
    """GeoJSON geometry, 3 decimals, wound as d3 wants (outer rings clockwise); slivers under ~1 km² dropped."""
    geom = shapely.orient_polygons(geom, exterior_cw=True)
    g = json.loads(gpd.GeoSeries([geom]).to_json())["features"][0]["geometry"]

    def walk(c):
        return [walk(x) for x in c] if isinstance(c[0], list) else [round(c[0], 3), round(c[1], 3)]
    g["coordinates"] = walk(g["coordinates"])
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    kept = []
    for poly in polys:
        rings = [r for r in poly if abs(ring_area(r)) >= 1e-4]
        if not rings or rings[0] is not poly[0]:
            continue
        kept.append([r if (ring_area(r) < 0) == (i == 0) else r[::-1] for i, r in enumerate(rings)])
    return {"type": "MultiPolygon", "coordinates": kept} if len(kept) != 1 else {"type": "Polygon",
                                                                                 "coordinates": kept[0]}


def shapes():
    s = gpd.read_parquet(MAIN / "data" / "raw" / "geo" / "regions_study.parquet")
    outlines = s.dissolve("state").geometry.simplify(SIMPLIFY, preserve_topology=True)
    s["geometry"] = s.geometry.simplify(SIMPLIFY, preserve_topology=True)
    return s, outlines


def write_map(s, outlines):
    m = {"counties": [{"id": r.region_fips, "g": rounded(r.geometry)} for r in s.itertuples()],
         "states": [{"name": n, "g": rounded(g)} for n, g in outlines.items()]}
    dump(m, SITE / "data" / "map.json")


# ---------- the 2025 record ----------

def load_2025():
    con = duckdb.connect()
    df = con.sql(f"""
        SELECT p.region_fips, p.block_start, p.y, p.held_out AS p_model, d.p_official
        FROM '{PRED}' p JOIN '{DECISIONS}' d USING (region_fips, block_start)
        ORDER BY region_fips, block_start""").df()
    df["region_fips"] = df.region_fips.astype(str)
    df["t"] = (df.block_start - pd.Timestamp("2025-01-01")) // pd.Timedelta(hours=1)
    return df


def alert_table(df, score, cut):
    """One row per alert (fips, start hour, peak chance, hit) and per outage (fips, onset, alerted, warning hours)."""
    fips, t, y, p = df.region_fips.to_numpy(), df.t.to_numpy(), df.y.to_numpy(), df[score].to_numpy()
    above = p >= cut
    a = np.flatnonzero(above)
    aid = ac.runs(fips[a], t[a], ac.MERGE_H)
    al = pd.DataFrame({"aid": aid, "fips": fips[a], "t": t[a], "y": y[a], "p": p[a]}).groupby("aid").agg(
        fips=("fips", "first"), start=("t", "min"), end=("t", "max"), peak=("p", "max"), hit=("y", "max"))
    o = np.flatnonzero(y == 1)
    oid = ac.runs(fips[o], t[o], 1)
    ev = pd.DataFrame({"oid": oid, "fips": fips[o], "t": t[o], "above": above[o], "row": o})
    out = ev.groupby("oid").agg(fips=("fips", "first"), onset=("t", "max"))
    out["onset"] += ac.LEAD_H
    first = ev[ev.above].groupby("oid").row.min()
    row_to_alert = pd.Series(aid, index=a)
    starts = al.start.reindex(row_to_alert.reindex(first.to_numpy()).to_numpy()).to_numpy()
    out["alerted"] = False
    out.loc[first.index, "alerted"] = True
    out["warning_h"] = np.nan
    out.loc[first.index, "warning_h"] = out.loc[first.index, "onset"].to_numpy() - starts
    return al.reset_index(drop=True), out.reset_index(drop=True)


def official_cut(df, n_hours):
    off = np.sort(df.p_official.to_numpy())[::-1]
    return off[min(n_hours, len(off)) - 1] if n_hours else np.inf


def month_of(t):
    return (pd.Timestamp("2025-01-01") + pd.to_timedelta(t, unit="h")).dt.month


def summary(al, out, n_counties):
    return {"alerts": int(len(al)), "per_county": round(len(al) / n_counties, 1),
            "hit": round(float(al.hit.mean()), 3) if len(al) else None,
            "outages": int(len(out)), "caught": round(float(out.alerted.mean()), 3) if len(out) else None,
            "warning_h": float(out.warning_h.median()) if out.alerted.any() else None}


def record(df, regions):
    n_c = df.region_fips.nunique()
    rec = {"year": 2025, "counties": n_c, "levels": [], "months": [], "states": []}
    tables = {}
    for name, cut in LEVELS:
        al, out = alert_table(df, "p_model", cut)
        hours = int((df.p_model >= cut).sum())
        oal, oout = alert_table(df, "p_official", official_cut(df, hours))
        tables[name] = (al, out)
        rec["levels"].append({"name": name, "chance": cut, "model": summary(al, out, n_c),
                              "official": summary(oal, oout, n_c), "alert_hours": hours})
        if name == "Elevated":
            for m in range(1, 13):
                a, o = al[month_of(al.start) == m], out[month_of(out.onset) == m]
                oa, oo = oal[month_of(oal.start) == m], oout[month_of(oout.onset) == m]
                rec["months"].append({"month": m, "alerts": int(len(a)), "hits": int(a.hit.sum()),
                                      "outages": int(len(o)), "caught": int(o.alerted.sum()),
                                      "official_caught": int(oo.alerted.sum()), "official_alerts": int(len(oa))})
            for st, ids in regions.groupby("state").region_fips:
                ids = set(ids)
                a, o = al[al.fips.isin(ids)], out[out.fips.isin(ids)]
                oo = oout[oout.fips.isin(ids)]
                rec["states"].append({"state": st, "abbr": abbr(st), "counties": len(ids & set(df.region_fips)),
                                      "alerts": int(len(a)), "hit": share(a.hit), "outages": int(len(o)),
                                      "caught": share(o.alerted), "official_caught": share(oo.alerted)})
    rec["states"].sort(key=lambda r: r["state"])
    return rec, tables


def share(s):
    return round(float(s.mean()), 3) if len(s) else None


_SEED = pd.read_csv(MAIN / "dbt" / "seeds" / "study_states.csv", dtype=str)
NAME_TO_ABBR = dict(zip(_SEED.state_name, _SEED.state_abbr, strict=True))


def abbr(state):
    return NAME_TO_ABBR.get(state, state)


# ---------- counties ----------

def county_facts(regions, place, history, tz, df, tables):
    t = regions.merge(place, on="region_fips", how="left", suffixes=("", "_p")).merge(history, on="region_fips",
                                                                                       how="left")
    tables_ = {"history": t, "regions": t, "place": t}
    pct = {}
    for key, col, tab, *_ in FACTS:
        v = tables_[tab][col]
        pct[key] = (v.rank(pct=True) * 100).round()
    al, out = tables["Elevated"]
    hi, _ = tables["High"]
    per = al.groupby("fips").agg(n=("hit", "size"), hits=("hit", "sum"))
    caught = out.groupby("fips").agg(outages=("alerted", "size"), caught=("alerted", "sum"))
    scored = set(df.region_fips)
    rows = {}
    for i, r in t.iterrows():
        f = r.region_fips
        z = tz.get(f, [r.region, abbr(r.state), "America/Chicago"])
        rows[f] = {
            "n": r.region, "s": abbr(r.state), "tz": z[2], "cust": int(r.customers),
            "facts": {k: [none(t.loc[i, col]), none(pct[k][i])] for k, col, *_ in FACTS},
            "unreliable": bool(r.hist_quiet_event_rate > UNRELIABLE) if pd.notna(r.hist_quiet_event_rate) else False,
            "y2025": {"alerts": int(per.n.get(f, 0)), "hits": int(per.hits.get(f, 0)),
                      "outages": int(caught.outages.get(f, 0)), "caught": int(caught.caught.get(f, 0)),
                      "high": int((hi.fips == f).sum())} if f in scored else None,
        }
    return rows


def none(v):
    if v is None or (isinstance(v, float) and math.isnan(v)) or pd.isna(v):
        return None
    return round(float(v), 3)


def county_alert_lists(tables):
    al, out = tables["Elevated"]
    base = pd.Timestamp("2025-01-01")
    lists = {}
    for f, g in al.groupby("fips"):
        lists[f] = [{"start": f"{base + pd.Timedelta(hours=int(r.start)):%Y-%m-%dT%HZ}",
                     "hours": int(r.end - r.start + 1), "peak": round(float(r.peak), 3), "hit": bool(r.hit)}
                    for r in g.sort_values("start").itertuples()]
    missed = {}
    for f, g in out[~out.alerted].groupby("fips"):
        missed[f] = [f"{base + pd.Timedelta(hours=int(o)):%Y-%m-%dT%HZ}" for o in g.onset.sort_values()]
    return lists, missed


# ---------- replays ----------

def replays(df, index):
    con = duckdb.connect(str(DB), read_only=True)
    d = duckdb.connect()
    out = []
    for rid, title, a, b in REPLAYS:
        t0, t1 = pd.Timestamp(a), pd.Timestamp(b)
        part = df[(df.block_start >= t0) & (df.block_start <= t1)]
        outs = con.sql(f"""
            SELECT region_fips, hour, pct_out, pct_out * customers / 100 AS n_out FROM marts.mart_study__region_1h
            WHERE hour BETWEEN '{t0}' AND '{t1 + pd.Timedelta(hours=8)}'""").df()
        warn = d.sql(f"""
            SELECT region_fips, block_start FROM '{DECISIONS}'
            WHERE block_start BETWEEN '{t0}' AND '{t1}' AND (warn_svr OR warn_tor OR warn_wind OR warn_winter)""").df()
        frames = []
        for h in pd.date_range(t0, t1, freq="h"):
            ph = part[part.block_start == h]
            ph = ph[ph.p_model >= 0.01]
            oh = outs[(outs.hour == h) & (outs.pct_out >= 5)]
            wh = warn[warn.block_start == h]
            frames.append({
                "h": f"{h:%Y-%m-%dT%HZ}",
                "p": [[index[f], int(round(v * 100))] for f, v in zip(ph.region_fips, ph.p_model, strict=True)
                      if f in index],
                "out": sorted(index[f] for f in oh.region_fips if f in index),
                "warn": sorted(index[f] for f in wh.region_fips if f in index),
                "n_out": int(outs[outs.hour == h].n_out.sum()),
            })
        # how the storm went: new outages in the span, how many had an Elevated alert first, and when
        span = df[(df.block_start >= t0 - pd.Timedelta(hours=12)) & (df.block_start <= t1)]
        al, o = alert_table(span.reset_index(drop=True), "p_model", LEVELS[0][1])
        o = o[o.onset >= ((t0 - pd.Timestamp("2025-01-01")) // pd.Timedelta(hours=1))]
        hours = int((span.p_model >= LEVELS[0][1]).sum())
        _, oo = alert_table(span.reset_index(drop=True), "p_official", official_cut(span, hours))
        oo = oo[oo.onset >= ((t0 - pd.Timestamp("2025-01-01")) // pd.Timedelta(hours=1))]
        out.append({"id": rid, "title": title, "frames": frames, "peak_out": max(f["n_out"] for f in frames),
                    "outages": int(len(o)), "caught": int(o.alerted.sum()),
                    "warning_h": float(o.warning_h.median()) if o.alerted.any() else None,
                    "official_caught": int(oo.alerted.sum())})
        print(f"replay {rid}: {len(frames)} hours, {len(o)} new outages, {int(o.alerted.sum())} alerted", flush=True)
    return out


# ---------- ZIP codes ----------

def zip_table(path, regions):
    z = pd.read_csv(path, sep="|", dtype=str, encoding="utf-8-sig",
                    usecols=["GEOID_ZCTA5_20", "GEOID_COUNTY_20", "AREALAND_PART"]).dropna()
    z["AREALAND_PART"] = z.AREALAND_PART.astype(float)
    z = z.sort_values("AREALAND_PART").drop_duplicates("GEOID_ZCTA5_20", keep="last")
    member = {}
    for r in regions.region_fips:
        for c in r.split("+"):
            member[c] = r
    z["region"] = z.GEOID_COUNTY_20.map(member)
    z = z.dropna(subset=["region"])
    return dict(zip(z.GEOID_ZCTA5_20, z.region, strict=True))


# ---------- the outlook image's shapes (storm-outage-live) ----------

def albers(lon, lat, lon0=-96.0, lat1=29.5, lat2=45.5, lat0=37.5):
    """Albers equal-area (the site's projection), unit sphere."""
    p1, p2, p0 = map(math.radians, (lat1, lat2, lat0))
    n = (math.sin(p1) + math.sin(p2)) / 2
    c = math.cos(p1) ** 2 + 2 * n * math.sin(p1)
    rho0 = math.sqrt(c - 2 * n * math.sin(p0)) / n
    lam, phi = np.radians(np.asarray(lon) - lon0), np.radians(np.asarray(lat))
    rho = np.sqrt(c - 2 * n * np.sin(phi)) / n
    return rho * np.sin(n * lam), rho0 - rho * np.cos(n * lam)


def svg_paths(geoms, scale, x0, y0):
    out = []
    for g in geoms:
        polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
        d = []
        for poly in polys:
            for ring in [poly.exterior, *poly.interiors]:
                x, y = albers(*np.asarray(ring.coords).T[:2])
                pts = [f"{(a - x0) * scale:.1f},{(y0 - b) * scale:.1f}" for a, b in zip(x, y, strict=True)]
                d.append("M" + "L".join(pts) + "Z")
        out.append("".join(d))
    return out


def outlook_shapes(s, outlines, folder):
    h = pd.read_parquet(STATIC / "history.parquet")
    allx, ally = [], []
    for g in outlines:
        x, y = albers(*np.asarray(g.envelope.exterior.coords).T[:2])
        allx += list(x)
        ally += list(y)
    width = 960
    scale = width / (max(allx) - min(allx))
    height = round((max(ally) - min(ally)) * scale)
    simple = s.geometry.simplify(0.03, preserve_topology=True)
    data = {"width": width, "height": height,
            "counties": dict(zip(s.region_fips, svg_paths(simple, scale, min(allx), max(ally)), strict=True)),
            "states": svg_paths(outlines.simplify(0.03, preserve_topology=True), scale, min(allx), max(ally)),
            "unreliable": sorted(h.region_fips[h.hist_quiet_event_rate > UNRELIABLE])}
    dump(data, Path(folder) / "outlook_shapes.json")


# ---------- county pages ----------

PAGE = (Path(__file__).resolve().parent / "usa_county_page.html")


def county_pages(rows, lists, missed):
    tpl = PAGE.read_text()
    folder = SITE / "county"
    folder.mkdir(parents=True, exist_ok=True)
    for f, r in rows.items():
        name = f"{r['n']}, {r['s']}"
        data = {"id": f, **r, "alerts2025": lists.get(f, []), "missed2025": missed.get(f, [])}
        page = (tpl.replace("{{NAME}}", html.escape(name)).replace("{{ID}}", f)
                .replace("{{DATA}}", json.dumps(data, separators=(",", ":")).replace("</", "<\\/")))
        (folder / f"{f.replace('+', '-')}.html").write_text(page)
    print(f"{len(rows)} county pages", flush=True)


def dump(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":"), allow_nan=False))
    print(f"wrote {path} ({path.stat().st_size / 1e6:.2f} MB)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zcta", required=True, help="Census tab20_zcta520_county20_natl.txt")
    ap.add_argument("--outlook", help="also write outlook_shapes.json into this folder (storm-outage-live usa/)")
    ap.add_argument("--only", nargs="*", help="build only these parts: map counties record replays zip pages")
    a = ap.parse_args()
    parts = set(a.only or ["map", "counties", "record", "replays", "zip", "pages"])

    s, outlines = shapes()
    if "map" in parts:
        write_map(s, outlines)
    if a.outlook:
        outlook_shapes(s, outlines, a.outlook)
    regions = pd.read_parquet(STATIC / "regions.parquet")
    all_regions = s[["region_fips", "region", "state"]]
    if "zip" in parts:
        dump(zip_table(a.zcta, all_regions), SITE / "data" / "zip.json")
    if not parts & {"counties", "record", "replays", "pages"}:
        return
    df = load_2025()
    print(f"{len(df):,} county-hours of 2025", flush=True)
    rec, tables = record(df, regions)
    if "record" in parts:
        dump(rec, SITE / "data" / "record.json")
    tz = json.loads(COUNTIES_TZ.read_text())
    rows = county_facts(regions, pd.read_parquet(STATIC / "place.parquet"),
                        pd.read_parquet(STATIC / "history.parquet"), tz, df, tables)
    if "counties" in parts:
        dump({"facts": [[k, label, more] for k, _, _, label, more in FACTS], "counties": rows},
             SITE / "data" / "counties.json")
    if "replays" in parts:
        index = {r.region_fips: i for i, r in enumerate(s.itertuples())}
        dump({"order": "map.json counties", "level": LEVELS[0][1], "storms": replays(df, index)},
             SITE / "data" / "replays.json")
    if "pages" in parts:
        lists, missed = county_alert_lists(tables)
        county_pages(rows, lists, missed)


if __name__ == "__main__":
    main()
