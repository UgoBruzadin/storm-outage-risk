-- HRRR storm ingredients summarized per region per 6-hour block:
--
--   gust / wind10       damaging surface wind
--   wind850             low-level jet (~1.5 km): wind that can mix down in storms
--   shear_0_6km         |wind at 500 hPa − wind at 10 m|: organized, severe storms need it
--   cape                convective energy = how strong updrafts can get
--   precip              heavy rain: saturated soil + wind topples trees
--   icing_hours         at or below freezing with precipitation: ice on lines and limbs
--   hail_hours          a simple proxy: instability + rain + low freezing level
--   precip_prev_*       rain in the 72 h / 7 days BEFORE the block: wet ground
--                       uproots trees in winds that dry ground would hold
--
-- A block is complete when all 6 hours exist; blocks before the weather
-- download covers a region simply have no row.
--
-- The antecedent-rain windows use RANGE (time), not ROWS (row count), so a gap
-- in the data shortens the window instead of stretching it further back. They
-- are NULL unless every block in the window is present.

WITH blocks AS (

SELECT
    region_fips,
    {{ block_6h('hour') }}                                         AS block_start,
    count(*)                                                       AS n_weather_hours,
    max(gust_ms)                                                   AS gust_max_ms,
    max(wind10_ms)                                                 AS wind10_max_ms,
    max(wind850_ms)                                                AS wind850_max_ms,
    max(sqrt((u500 - u10) ^ 2 + (v500 - v10) ^ 2))                 AS shear_0_6km_max_ms,
    max(cape_jkg)                                                  AS cape_max_jkg,
    sum(precip_mm)                                                 AS precip_sum_mm,
    max(precip_mm)                                                 AS precip_max_1h_mm,
    min(temp_c)                                                    AS temp_min_c,
    avg(temp_c)                                                    AS temp_mean_c,
    min(freezing_level_m)                                          AS freezing_level_min_m,
    count(*) FILTER (WHERE temp_c <= 0 AND precip_mm > 0)          AS icing_hours,
    count(*) FILTER (WHERE cape_jkg >= 500 AND precip_mm >= 2
                       AND freezing_level_m <= 3500)               AS hail_hours
FROM {{ ref('stg_hrrr__hourly') }}
GROUP BY ALL

)

SELECT
    *,
    CASE WHEN count(*) OVER prev_72h = 12 THEN sum(precip_sum_mm) OVER prev_72h END AS precip_prev_72h_mm,
    CASE WHEN count(*) OVER prev_7d  = 28 THEN sum(precip_sum_mm) OVER prev_7d  END AS precip_prev_7d_mm
FROM blocks
WINDOW
    prev_72h AS (PARTITION BY region_fips ORDER BY block_start
                 RANGE BETWEEN INTERVAL 72 HOURS PRECEDING AND INTERVAL 6 HOURS PRECEDING),
    prev_7d  AS (PARTITION BY region_fips ORDER BY block_start
                 RANGE BETWEEN INTERVAL 168 HOURS PRECEDING AND INTERVAL 6 HOURS PRECEDING)
