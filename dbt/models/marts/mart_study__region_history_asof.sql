-- Each region's outage track record AS OF the start of each year: the same
-- measures as the resilience scorecard, computed from the 3 years before
-- January 1 of as_of_year only. A model row in year Y joins as_of_year = Y,
-- so its history never includes the year it predicts (or anything later),
-- and history features can be used on any training years.
--
--   as_of_year 2024 -> history 2021-01-01 .. 2023-12-31
--   as_of_year 2020 -> history 2017-01-01 .. 2019-12-31 (EAGLE-I coverage is
--                      patchier before 2020; unknown blocks are skipped and
--                      rates are per year actually observed)
--
-- Measures and the event definition (>= 1% out, gaps-and-islands) match
-- mart_study__region_resilience; see that model for their meaning.

{% set years_back = 3 %}

WITH as_of AS (
    SELECT unnest(generate_series(2017, 2026)) AS as_of_year
),
blocks AS (
    SELECT
        a.as_of_year,
        m.region_fips,
        m.block_start,
        m.customers,
        m.mean_out,
        m.peak_pct_out >= 1          AS is_event,
        m.storm_reports > 0          AS storm
    FROM {{ ref('mart_study__region_6h') }} AS m
    JOIN as_of AS a
      ON m.block_start >= make_timestamp(a.as_of_year - {{ years_back }}, 1, 1, 0, 0, 0)
     AND m.block_start <  make_timestamp(a.as_of_year, 1, 1, 0, 0, 0)
    WHERE m.peak_pct_out IS NOT NULL
),
flagged AS (
    SELECT
        *,
        is_event AND coalesce(
            lag(block_start) OVER (PARTITION BY as_of_year, region_fips, is_event ORDER BY block_start)
                <> block_start - INTERVAL 6 HOUR, true)                  AS event_start
    FROM blocks
),
numbered AS (
    SELECT *, sum(event_start::INT) OVER (PARTITION BY as_of_year, region_fips ORDER BY block_start) AS event_no
    FROM flagged
),
events AS (
    SELECT
        as_of_year,
        region_fips,
        event_no,
        min(block_start)                          AS start_at,
        max(block_start) + INTERVAL 6 HOUR        AS end_at
    FROM numbered
    WHERE is_event
    GROUP BY ALL
),
event_stats AS (
    SELECT
        as_of_year,
        region_fips,
        avg(CASE WHEN next_start - end_at <= INTERVAL 7 DAY THEN 1 ELSE 0 END) AS repeat_7d_share
    FROM (
        SELECT *, lead(start_at) OVER (PARTITION BY as_of_year, region_fips ORDER BY start_at) AS next_start
        FROM events
    )
    GROUP BY ALL
),
block_stats AS (
    SELECT
        as_of_year,
        region_fips,
        count(*) * 6 / 8766.0                                                AS years_observed,
        sum(mean_out) * 6 / any_value(customers) / (count(*) * 6 / 8766.0)   AS hours_out_per_customer,
        count(*) FILTER (WHERE event_start) / (count(*) * 6 / 8766.0)        AS events_per_year,
        avg(is_event::INT) FILTER (WHERE storm)                              AS storm_hit_rate,
        avg(is_event::INT) FILTER (WHERE NOT storm)                          AS quiet_event_rate
    FROM numbered
    GROUP BY ALL
)
SELECT
    b.as_of_year,
    b.region_fips,
    make_date(b.as_of_year - {{ years_back }}, 1, 1)  AS history_start,
    make_date(b.as_of_year, 1, 1)                     AS history_end,
    b.years_observed,
    b.hours_out_per_customer,
    b.events_per_year,
    b.storm_hit_rate,
    b.quiet_event_rate,
    e.repeat_7d_share
FROM block_stats AS b
LEFT JOIN event_stats AS e USING (as_of_year, region_fips)
