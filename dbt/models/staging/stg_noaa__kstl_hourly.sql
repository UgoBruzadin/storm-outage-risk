-- Weather at St. Louis Lambert airport (KSTL), one row per hour. Used by the
-- legacy St. Louis hourly prototype (legacy/).
--
-- Unpacking pattern, read inside-out:
--   split_part(TMP, ',', 1)   take piece 1 before the comma   '+0039'
--   nullif(..., '+9999')      NOAA's "missing" code -> NULL
--   ::INT / 10.0              text -> number, NOAA stores values x10   3.9
--
-- Timing: the regular report (FM-15) comes at :51; +9 minutes labels it with
-- the next hour, so weather is always from before the outage it's paired with.
-- QUALIFY keeps the earliest report when an hour has two FM-15s.
-- Gust NULL means "no gust", so it falls back to the steady wind.
-- Thunder comes from the METAR text in REM (the coded MW1 field misses it).

SELECT
    date_trunc('hour', CAST("DATE" AS TIMESTAMP) + INTERVAL 9 MINUTE)  AS hour,
    nullif(split_part(TMP, ',', 1), '+9999')::INT / 10.0                AS temp_c,
    nullif(split_part(WND, ',', 4), '9999')::INT / 10.0                 AS wind_ms,
    coalesce(
        nullif(split_part(OC1, ',', 1), '9999')::INT / 10.0,
        nullif(split_part(WND, ',', 4), '9999')::INT / 10.0
    )                                                                   AS gust_ms,
    CASE WHEN split_part(AA1, ',', 1) = '01'
         THEN nullif(split_part(AA1, ',', 2), '9999')::INT / 10.0
    END                                                                 AS precip_mm,
    coalesce(regexp_matches(REM, ' (\+|-|VC)?TS'), false)               AS thunder
FROM {{ source('noaa', 'kstl_observations') }}
WHERE REPORT_TYPE = 'FM-15'
QUALIFY row_number() OVER (PARTITION BY hour ORDER BY "DATE") = 1
