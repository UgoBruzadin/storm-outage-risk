-- The moving-window modeling table: one row per region per hour from 2018 (when the
-- HRRR weather starts). A row is a decision made at the start of `hour`: every
-- feature uses only what had happened by then, and the labels describe the 6 hours
-- that start L hours later, for leads L = 0, 1, 2, 3 and 6.
--
-- Outages per hour (pct_out): the worst 15-min snapshot in the hour as % of
-- customers. NULL = unknown: EAGLE-I down nationally that hour (< 2 of 4 snapshots),
-- a blank count, or a count over 1.5x the customers (as in mart_study__region_6h).
--
-- Features (known at `hour`):
--   weather    the 6-hour summaries of int_study__weather_6h over the 6 hours before
--              `hour`; NULL unless all 6 exist. precip_prev_72h_mm: the 72 hours before.
--              Hourly rain over 100 mm is treated as unknown (an archive artifact)
--   recent     pct_out_now (the hour before), the worst hour in the past 24 h and 7 days
--   since      hours since the region last had >= 1% out (capped at 720 = 30 days) and
--              how big that outage was. NULL when over 10% of the hours since were
--              unknown: a tracker gap doesn't reset the clock, it hides it
--   official   NWS warnings in force and the latest SPC outlook (int_study__nws_1h)
--   place      as in mart_study__region_6h
--
-- Labels, per lead L (the window: hours hour+L ... hour+L+5):
--   fut_max_pct_L    worst hour in the window (NULL unless >= 3 of its 6 hours are known)
--   start_pct_L      the hour just before the window: whether the region was already out
--                    when the window began (a new outage needs it below the threshold)
-- For L > 0, start_pct_L is after `hour`: it only selects which rows are scored as new
-- outages, it is never a feature.

WITH hours AS (
    SELECT hour, eaglei_ok
    FROM {{ ref('int_eaglei__hours_1h') }}
    WHERE hour >= TIMESTAMP '2018-01-01'
),
grid AS (
    SELECT
        r.region_fips,
        h.hour,
        r.customers,
        CASE
            WHEN NOT h.eaglei_ok        THEN NULL
            WHEN o.region_fips IS NULL  THEN 0
            ELSE o.peak_out
        END                                                  AS peak_out
    FROM {{ ref('int_study__regions') }} AS r
    CROSS JOIN hours AS h
    LEFT JOIN {{ ref('int_study__outages_1h') }} AS o
           ON o.region_fips = r.region_fips AND o.hour = h.hour
),
pct AS (
    SELECT
        g.*,
        CASE WHEN g.peak_out IS NULL OR g.peak_out > 1.5 * g.customers THEN NULL
             ELSE least(100.0, 100.0 * g.peak_out / g.customers) END          AS pct_out,
        w.gust_ms, w.wind10_ms, w.wind850_ms, w.cape_jkg, w.temp_c, w.freezing_level_m,
        -- over 100 mm in an hour is beyond any record here (the archive has ~1,000 such hours,
        -- up to 340 mm, mostly with light winds): an artifact, so unknown
        CASE WHEN w.precip_mm <= 100 THEN w.precip_mm END                   AS precip_mm,
        sqrt((w.u500 - w.u10) ^ 2 + (w.v500 - w.v10) ^ 2)                   AS shear_ms
    FROM grid AS g
    LEFT JOIN {{ ref('stg_hrrr__hourly') }} AS w USING (region_fips, hour)
),
marked AS (
    SELECT
        *,
        sum((pct_out IS NULL)::INT) OVER (PARTITION BY region_fips ORDER BY hour)  AS cum_unknown,
        CASE WHEN pct_out >= 1 THEN hour END                                        AS outage_hour,
        CASE WHEN pct_out >= 1 THEN pct_out END                                     AS outage_pct
    FROM pct
),
features AS (
    SELECT
        region_fips,
        hour,
        customers,
        pct_out,

        -- weather: the 6 hours before `hour`
        count(gust_ms) OVER w6 = 6                                                  AS has_weather,
        max(gust_ms) OVER w6                                                        AS gust_max_ms,
        max(wind10_ms) OVER w6                                                      AS wind10_max_ms,
        max(wind850_ms) OVER w6                                                     AS wind850_max_ms,
        max(shear_ms) OVER w6                                                       AS shear_0_6km_max_ms,
        max(cape_jkg) OVER w6                                                       AS cape_max_jkg,
        sum(precip_mm) OVER w6                                                      AS precip_sum_mm,
        max(precip_mm) OVER w6                                                      AS precip_max_1h_mm,
        min(temp_c) OVER w6                                                         AS temp_min_c,
        avg(temp_c) OVER w6                                                         AS temp_mean_c,
        min(freezing_level_m) OVER w6                                               AS freezing_level_min_m,
        count(*) FILTER (WHERE temp_c <= 0 AND precip_mm > 0) OVER w6               AS icing_hours,
        count(*) FILTER (WHERE cape_jkg >= 500 AND precip_mm >= 2
                           AND freezing_level_m <= 3500) OVER w6                    AS hail_hours,
        CASE WHEN count(precip_mm) OVER w72 = 72 THEN sum(precip_mm) OVER w72 END   AS precip_prev_72h_mm,

        -- recent outages
        lag(pct_out) OVER w                                                         AS pct_out_now,
        max(pct_out) OVER w24                                                       AS max_pct_out_prev_24h,
        max(pct_out) OVER w168                                                      AS max_pct_out_prev_7d,

        -- the last outage before `hour`, and how many unknown hours since
        last_value(outage_hour IGNORE NULLS) OVER wall                              AS last_outage_hour,
        last_value(outage_pct IGNORE NULLS) OVER wall                               AS last_outage_pct,
        lag(cum_unknown) OVER w - last_value(CASE WHEN outage_hour IS NOT NULL THEN cum_unknown END
                                            IGNORE NULLS) OVER wall                 AS unknown_since_outage,
        sum((pct_out IS NULL)::INT) OVER w720                                       AS unknown_prev_720h,

        -- labels: the window [hour + L, hour + L + 6)
        {% for lead in [0, 1, 2, 3, 6] %}
        CASE WHEN count(pct_out) OVER f{{ lead }} >= 3 THEN max(pct_out) OVER f{{ lead }} END AS fut_max_pct_{{ lead }},
        {% if lead == 0 %}lag(pct_out) OVER w{% elif lead == 1 %}pct_out{% else %}lead(pct_out, {{ lead - 1 }}) OVER w{% endif %} AS start_pct_{{ lead }},
        {% endfor %}
    FROM marked
    WINDOW
        w    AS (PARTITION BY region_fips ORDER BY hour),
        w6   AS (w ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING),
        w24  AS (w ROWS BETWEEN 24 PRECEDING AND 1 PRECEDING),
        w72  AS (w ROWS BETWEEN 72 PRECEDING AND 1 PRECEDING),
        w168 AS (w ROWS BETWEEN 168 PRECEDING AND 1 PRECEDING),
        w720 AS (w ROWS BETWEEN 720 PRECEDING AND 1 PRECEDING),
        wall AS (w ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
        {% for lead in [0, 1, 2, 3, 6] %}
        f{{ lead }} AS (w ROWS BETWEEN {{ lead }} FOLLOWING AND {{ lead + 5 }} FOLLOWING){{ "," if not loop.last }}
        {% endfor %}
)
SELECT
    f.* EXCLUDE (last_outage_hour, unknown_since_outage, unknown_prev_720h),
    -- hours since the last >= 1% outage, capped at 30 days; unknown if the tracker missed > 10% of them
    CASE
        WHEN f.last_outage_hour IS NOT NULL AND date_diff('hour', f.last_outage_hour, f.hour) <= 720
            THEN CASE WHEN f.unknown_since_outage <= 0.1 * date_diff('hour', f.last_outage_hour, f.hour)
                      THEN date_diff('hour', f.last_outage_hour, f.hour) END
        WHEN f.unknown_prev_720h <= 72 THEN 720
    END                                                                             AS hours_since_outage,

    -- place
    r.region,
    r.state,
    r.land_km2,
    r.housing_per_km2,
    r.share_homes_pre1960,
    r.median_year_built,
    r.canopy_mean_pct,
    r.canopy_dense_share,

    -- official forecasts at `hour`
    coalesce(n.warn_svr, false)                                     AS warn_svr,
    coalesce(n.warn_tor, false)                                     AS warn_tor,
    coalesce(n.warn_wind, false)                                    AS warn_wind,
    coalesce(n.warn_winter, false)                                  AS warn_winter,
    n.spc_cat,
    n.spc_wind_prob,
    n.spc_tor_prob,
    n.spc_hail_prob,

    -- calendar
    month(f.hour)                                                   AS month,
    dayofweek(f.hour)                                               AS day_of_week,
    hour(f.hour)                                                    AS hour_utc
FROM features AS f
JOIN {{ ref('int_study__regions') }}  AS r USING (region_fips)
LEFT JOIN {{ ref('int_study__nws_1h') }} AS n USING (region_fips, hour)
