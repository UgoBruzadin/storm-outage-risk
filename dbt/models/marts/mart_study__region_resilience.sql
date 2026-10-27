-- Resilience scorecard: how each study-area region has fared, from its outage
-- history, over 2020–2025 (the years with full EAGLE-I coverage and weather).
-- For display only: the model's history features come from
-- mart_study__region_history_asof, which never looks past a row's own year.
-- Change the window with:
--   pixi run dbt build --vars '{history_start: "2020-01-01", history_end: "2024-01-01"}'
--
-- An "event" is a run of consecutive 6-hour blocks with >= 1% of customers
-- out (gaps-and-islands: a new event starts whenever the previous block
-- wasn't an event block).
--
--   hours_out_per_customer   customer-hours lost per customer per year (a SAIDI-like burden)
--   events_per_year          how often the power fails at scale
--   storm_hit_rate           P(event | NOAA storm report in the block) — how often a
--                            reported storm turns into an outage here; compares places
--                            under similar weather, so it's closer to "vulnerability"
--   quiet_event_rate         P(event | no storm report) — outages without reported storms
--   median_event_hours       typical event length (6-hour resolution)
--   repeat_7d_share          share of events followed by another within 7 days
--
-- Blocks with unknown outages (EAGLE-I down, blank or suspect counts) are skipped.

{% set history_start = var('history_start', '2020-01-01') %}
{% set history_end = var('history_end', '2026-01-01') %}

WITH blocks AS (
    SELECT
        region_fips,
        block_start,
        customers,
        mean_out,
        peak_pct_out >= 1          AS is_event,
        storm_reports > 0          AS storm
    FROM {{ ref('mart_study__region_6h') }}
    WHERE peak_pct_out IS NOT NULL
      AND block_start >= TIMESTAMP '{{ history_start }}'
      AND block_start <  TIMESTAMP '{{ history_end }}'
),
flagged AS (
    -- an event starts when this block is an event and the previous 6 hours weren't
    SELECT
        *,
        is_event AND coalesce(
            lag(block_start) OVER (PARTITION BY region_fips, is_event ORDER BY block_start)
                <> block_start - INTERVAL 6 HOUR, true)                  AS event_start
    FROM blocks
),
numbered AS (
    SELECT *, sum(event_start::INT) OVER (PARTITION BY region_fips ORDER BY block_start) AS event_no
    FROM flagged
),
events AS (
    SELECT
        region_fips,
        event_no,
        min(block_start)                          AS start_at,
        max(block_start) + INTERVAL 6 HOUR        AS end_at,
        6 * count(*)                              AS event_hours
    FROM numbered
    WHERE is_event
    GROUP BY ALL
),
event_stats AS (
    SELECT
        region_fips,
        median(event_hours)                                                  AS median_event_hours,
        avg(CASE WHEN next_start - end_at <= INTERVAL 7 DAY THEN 1 ELSE 0 END) AS repeat_7d_share
    FROM (
        SELECT *, lead(start_at) OVER (PARTITION BY region_fips ORDER BY start_at) AS next_start
        FROM events
    )
    GROUP BY region_fips
),
block_stats AS (
    SELECT
        region_fips,
        any_value(customers)                                                 AS customers,
        count(*) * 6 / 8766.0                                                AS years_observed,
        sum(mean_out) * 6 / any_value(customers) / (count(*) * 6 / 8766.0)   AS hours_out_per_customer,
        count(*) FILTER (WHERE event_start) / (count(*) * 6 / 8766.0)        AS events_per_year,
        avg(is_event::INT) FILTER (WHERE storm)                              AS storm_hit_rate,
        avg(is_event::INT) FILTER (WHERE NOT storm)                          AS quiet_event_rate,
        count(*) FILTER (WHERE storm)                                        AS storm_blocks
    FROM numbered
    GROUP BY region_fips
)
SELECT
    r.region_fips,
    r.region,
    r.state,
    b.customers,
    '{{ history_start }}'::DATE                AS history_start,
    '{{ history_end }}'::DATE                  AS history_end,
    b.years_observed,
    b.hours_out_per_customer,
    b.events_per_year,
    b.storm_hit_rate,
    b.quiet_event_rate,
    b.storm_blocks,
    e.median_event_hours,
    e.repeat_7d_share,
    r.canopy_mean_pct,
    r.share_homes_pre1960,
    r.housing_per_km2
FROM {{ ref('int_study__regions') }} AS r
LEFT JOIN block_stats AS b USING (region_fips)
LEFT JOIN event_stats AS e USING (region_fips)
