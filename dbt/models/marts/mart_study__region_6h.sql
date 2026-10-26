-- The modeling table: every study-area region x every 6-hour block, Nov 2014 →
-- Dec 2025 (~3.5M rows). One row = "this place, these 6 hours".
--
-- Label (what happened):
--   peak_out  worst moment in the block. Three cases, checked in order:
--     EAGLE-I down (block heartbeat < 12 snapshots)  -> NULL: unknown
--     EAGLE-I up, no outage row for this region       -> 0
--     otherwise                                       -> the value (NULL if every count was blank)
--   peak_pct_out  peak_out as % of customers, capped at 100. NULL when the
--     count is over 1.5x the customer count (peak_suspect): either a one-off
--     glitch (Boone Co. shows 311,925 out of ~122k customers on 2019-12-13)
--     or a customer count that's too low (Worth Co., MO: 418 in MCC.csv for
--     ~2,000 residents). Either way the percentage can't be trusted.
--
-- Features (what a model may use):
--   weather    HRRR storm ingredients for the block (NULL before the weather
--              download covers it — check has_weather)
--   place      customers, canopy, housing age/density — fixed per region
--   calendar   month, hour of block (UTC)
--
-- Context (NOT model inputs — reported after the fact, so using them would
-- leak the answer): storm_* counts from NOAA Storm Events.

WITH grid AS (
    SELECT
        r.region_fips,
        b.block_start,
        b.n_snapshots,
        CASE
            WHEN NOT b.eaglei_ok        THEN NULL
            WHEN o.region_fips IS NULL  THEN 0
            ELSE o.peak_out
        END                                                  AS peak_out,
        CASE WHEN b.eaglei_ok THEN coalesce(o.mean_out, 0) END AS mean_out,
        r.customers
    FROM {{ ref('int_study__regions') }} AS r
    CROSS JOIN {{ ref('int_eaglei__blocks_6h') }} AS b
    LEFT JOIN {{ ref('int_study__outages_6h') }} AS o
           ON o.region_fips = r.region_fips
          AND o.block_start = b.block_start
)
SELECT
    g.region_fips,
    g.block_start,

    -- label
    g.peak_out,
    g.peak_out > 1.5 * g.customers                                  AS peak_suspect,
    -- the IS NULL check matters: DuckDB's least() skips NULLs, so
    -- least(100, NULL) is 100 — every blank count would become "100% out"
    CASE WHEN g.peak_out IS NULL OR g.peak_out > 1.5 * g.customers THEN NULL
         ELSE least(100.0, 100.0 * g.peak_out / g.customers) END     AS peak_pct_out,
    g.mean_out,
    g.n_snapshots                                                   AS eaglei_snapshots,

    -- weather (HRRR)
    coalesce(w.n_weather_hours = 6, false)                          AS has_weather,
    w.gust_max_ms,
    w.wind10_max_ms,
    w.wind850_max_ms,
    w.shear_0_6km_max_ms,
    w.cape_max_jkg,
    w.precip_sum_mm,
    w.precip_max_1h_mm,
    w.temp_min_c,
    w.temp_mean_c,
    w.freezing_level_min_m,
    w.icing_hours,
    w.hail_hours,

    -- place
    r.region,
    r.state,
    r.customers,
    r.land_km2,
    r.housing_per_km2,
    r.share_homes_pre1960,
    r.median_year_built,
    r.canopy_mean_pct,
    r.canopy_dense_share,

    -- calendar
    month(g.block_start)                                            AS month,
    hour(g.block_start)                                             AS block_hour_utc,

    -- context: storm reports (not features)
    coalesce(s.n_reports, 0)                                        AS storm_reports,
    coalesce(s.n_tstm_wind, 0)                                      AS storm_tstm_wind,
    s.max_tstm_wind_kt                                              AS storm_max_wind_kt,
    coalesce(s.n_hail, 0)                                           AS storm_hail,
    coalesce(s.n_tornado, 0)                                        AS storm_tornado,
    coalesce(s.n_high_wind, 0)                                      AS storm_high_wind,
    coalesce(s.n_winter, 0)                                         AS storm_winter
FROM grid AS g
JOIN {{ ref('int_study__regions') }}               AS r USING (region_fips)
LEFT JOIN {{ ref('int_study__weather_6h') }}       AS w USING (region_fips, block_start)
LEFT JOIN {{ ref('int_study__storm_events_6h') }}  AS s USING (region_fips, block_start)
