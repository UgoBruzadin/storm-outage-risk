-- Official forecasts per region per 6-hour block, as known when the block starts:
-- the warnings in force at that moment, and the latest SPC outlook.
--
-- Warnings: county warnings carry the county directly; zone warnings (high wind,
-- winter, ice) go to every county in the zone, as in int_study__storm_events_6h.
-- A warning counts for a block only if it was issued BEFORE the block started
-- and hadn't expired: issue < block_start < expire. Counting any warning that
-- touches the block would mostly capture warnings issued once the storm (and
-- often the outage) had already arrived: of 1,445 new >= 5% outages in 2025,
-- 335 had a severe thunderstorm or tornado warning somewhere in the block, but
-- only 65 had one in force at its start.
--
-- Outlook: the latest Day 1 product issued BEFORE the block starts and valid at
-- its start, so it is a genuine forecast (hours of lead time). A product that
-- doesn't reach a region carries 0, so "the newest outlook dropped this county"
-- reads as no risk rather than falling back to an older product.

WITH warning_counties AS (
    SELECT st.state_fips || w.ugc_number AS fips_code, w.*
    FROM {{ ref('stg_nws__warnings') }} AS w
    JOIN {{ ref('study_states') }} AS st USING (state_abbr)
    WHERE w.ugc_type = 'C'

    UNION ALL BY NAME

    SELECT z.fips_code, w.*
    FROM {{ ref('stg_nws__warnings') }} AS w
    JOIN {{ ref('stg_noaa__zone_county') }} AS z
      ON z.zone_id = w.state_abbr || w.ugc_number
    WHERE w.ugc_type = 'Z'
),
warning_blocks AS (
    SELECT
        {{ region_fips('fips_code') }}                                   AS region_fips,
        -- block starts strictly inside (issue, expire); empty for most warnings,
        -- which last under an hour and don't cross a block boundary
        unnest(generate_series({{ block_6h('issue_utc') }} + INTERVAL 6 HOUR,
                               {{ block_6h("expire_utc - INTERVAL 1 MINUTE") }},
                               INTERVAL 6 HOUR))                         AS block_start,
        phenomena
    FROM warning_counties
    WHERE expire_utc > issue_utc
),
warnings AS (
    SELECT
        region_fips,
        block_start,
        bool_or(phenomena = 'SV')                         AS warn_svr,
        bool_or(phenomena = 'TO')                         AS warn_tor,
        bool_or(phenomena = 'HW')                         AS warn_wind,
        bool_or(phenomena IN ('IS', 'WS', 'BZ'))          AS warn_winter
    FROM warning_blocks
    GROUP BY ALL
),
products AS (
    SELECT DISTINCT issued_utc, valid_from, valid_to FROM {{ ref('stg_spc__day1_outlooks') }}
),
outlook_for_block AS (                -- latest product issued before the block and valid at its start
    SELECT b.block_start, max(p.issued_utc) AS issued_utc
    FROM {{ ref('int_eaglei__blocks_6h') }} AS b
    JOIN products AS p
      ON p.issued_utc < b.block_start
     AND b.block_start >= p.valid_from AND b.block_start < p.valid_to
    GROUP BY 1
),
outlooks AS (
    SELECT
        o.region_fips,
        ob.block_start,
        o.spc_cat,
        o.spc_wind_prob,
        o.spc_tor_prob,
        o.spc_hail_prob,
        date_diff('minute', ob.issued_utc, ob.block_start) / 60.0  AS spc_lead_hours
    FROM outlook_for_block AS ob
    JOIN {{ ref('stg_spc__day1_outlooks') }} AS o USING (issued_utc)
)
SELECT
    region_fips,
    block_start,
    coalesce(w.warn_svr, false)                          AS warn_svr,
    coalesce(w.warn_tor, false)                          AS warn_tor,
    coalesce(w.warn_wind, false)                         AS warn_wind,
    coalesce(w.warn_winter, false)                       AS warn_winter,
    o.spc_cat,
    o.spc_wind_prob,
    o.spc_tor_prob,
    o.spc_hail_prob,
    o.spc_lead_hours
FROM outlooks AS o
FULL OUTER JOIN warnings AS w USING (region_fips, block_start)
