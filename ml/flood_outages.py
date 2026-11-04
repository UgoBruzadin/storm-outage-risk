"""How many new outages come with flood reports and no other storm? (docs/experiments.md, E46)

Before adding flood data, a check on the storm reports already in the warehouse: for every fresh new outage in
2020-2025, was a Flood or Flash Flood report filed in that county within 6 hours, and was a wind, hail, tornado or
winter report filed in the same 18 hours of 6-hour blocks? Reports are filed by people and can be missed, so this is a
rough size, not a cause of each outage.

Usage: pixi run python -m ml.flood_outages
Writes ml/results/flood_outages.csv.
"""
import duckdb
import pandas as pd

from ml import data
from ml.moving_window import onset_hours

YEARS = range(2020, 2026)
WINDOW_H = 6


def main():
    onsets = pd.concat([onset_hours(y) for y in YEARS], ignore_index=True)
    con = duckdb.connect(str(data.DB), read_only=True)
    con.register("onsets", onsets)
    d = con.sql(f"""
        WITH floods AS (
            SELECT CASE WHEN state_fips || cz_fips IN ('29189', '29510') THEN '29189+29510'
                        ELSE state_fips || cz_fips END AS region_fips, begin_utc, end_utc
            FROM staging.stg_noaa__storm_events
            WHERE event_type IN ('Flood', 'Flash Flood') AND cz_type = 'C'
        )
        SELECT o.region_fips, o.hour,
            EXISTS (SELECT 1 FROM floods f WHERE f.region_fips = o.region_fips
                    AND f.begin_utc <= o.hour + INTERVAL {WINDOW_H} HOUR
                    AND f.end_utc >= o.hour - INTERVAL {WINDOW_H} HOUR) AS flood,
            EXISTS (SELECT 1 FROM intermediate.int_study__storm_events_6h s WHERE s.region_fips = o.region_fips
                    AND s.block_start BETWEEN o.hour - INTERVAL 12 HOUR AND o.hour + INTERVAL {WINDOW_H} HOUR
                    AND s.n_tstm_wind + s.n_hail + s.n_tornado + s.n_high_wind + s.n_winter > 0) AS other
        FROM onsets o
    """).df()
    con.close()
    d["year"] = d.hour.dt.year
    rows = [{"period": str(y), "new_outages": len(g), "any_flood_report": int(g.flood.sum()),
             "flood_report_no_other_storm": int((g.flood & ~g.other).sum()),
             "other_storm_report": int(g.other.sum()), "no_report": int((~g.flood & ~g.other).sum())}
            for y, g in [*d.groupby("year"), ("2020-2025", d)]]
    out = pd.DataFrame(rows)
    out["share_flood_no_other"] = out.flood_report_no_other_storm / out.new_outages
    out["share_any_flood"] = out.any_flood_report / out.new_outages
    out.to_csv(data.ROOT / "ml" / "results" / "flood_outages.csv", index=False)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
