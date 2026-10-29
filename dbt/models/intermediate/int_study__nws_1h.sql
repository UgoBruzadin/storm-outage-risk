-- Official forecasts per region at the start of each hour, as int_study__nws_6h
-- does for 6-hour blocks: warnings in force at that moment (issued before it and
-- not expired), and the latest SPC Day 1 outlook issued before it and valid at it.

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
warning_hours AS (
    SELECT
        {{ region_fips('fips_code') }}                                   AS region_fips,
        -- hour starts strictly inside (issue, expire)
        unnest(generate_series(date_trunc('hour', issue_utc) + INTERVAL 1 HOUR,
                               date_trunc('hour', expire_utc - INTERVAL 1 MINUTE),
                               INTERVAL 1 HOUR))                         AS hour,
        phenomena
    FROM warning_counties
    WHERE expire_utc > issue_utc
),
warnings AS (
    SELECT
        region_fips,
        hour,
        bool_or(phenomena = 'SV')                         AS warn_svr,
        bool_or(phenomena = 'TO')                         AS warn_tor,
        bool_or(phenomena = 'HW')                         AS warn_wind,
        bool_or(phenomena IN ('IS', 'WS', 'BZ'))          AS warn_winter
    FROM warning_hours
    GROUP BY ALL
),
products AS (
    SELECT DISTINCT issued_utc, valid_from, valid_to FROM {{ ref('stg_spc__day1_outlooks') }}
),
outlook_for_hour AS (
    SELECT h.hour, max(p.issued_utc) AS issued_utc
    FROM {{ ref('int_eaglei__hours_1h') }} AS h
    JOIN products AS p
      ON p.issued_utc < h.hour
     AND h.hour >= p.valid_from AND h.hour < p.valid_to
    GROUP BY 1
),
outlooks AS (
    SELECT
        o.region_fips,
        oh.hour,
        o.spc_cat,
        o.spc_wind_prob,
        o.spc_tor_prob,
        o.spc_hail_prob
    FROM outlook_for_hour AS oh
    JOIN {{ ref('stg_spc__day1_outlooks') }} AS o USING (issued_utc)
)
SELECT
    region_fips,
    hour,
    coalesce(w.warn_svr, false)                          AS warn_svr,
    coalesce(w.warn_tor, false)                          AS warn_tor,
    coalesce(w.warn_wind, false)                         AS warn_wind,
    coalesce(w.warn_winter, false)                       AS warn_winter,
    o.spc_cat,
    o.spc_wind_prob,
    o.spc_tor_prob,
    o.spc_hail_prob
FROM outlooks AS o
FULL OUTER JOIN warnings AS w USING (region_fips, hour)
