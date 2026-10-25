-- HRRR storm ingredients per region per hour (Open-Meteo, UTC, m/s).
-- Read as text (see _sources.yml), so every column is cast here.
-- Wind direction is where the wind blows FROM, in degrees; we turn speed +
-- direction into east (u) and north (v) components so winds at two heights
-- can be subtracted: |wind aloft − wind at surface| = vertical wind shear.

WITH typed AS (
    SELECT
        region_fips,
        CAST("time" AS TIMESTAMP)                  AS hour,
        TRY_CAST(wind_gusts_10m        AS DOUBLE)  AS gust_ms,
        TRY_CAST(wind_speed_10m        AS DOUBLE)  AS wind10_ms,
        TRY_CAST(wind_direction_10m    AS DOUBLE)  AS wind10_dir,
        TRY_CAST(wind_speed_850hPa     AS DOUBLE)  AS wind850_ms,
        TRY_CAST(wind_speed_500hPa     AS DOUBLE)  AS wind500_ms,
        TRY_CAST(wind_direction_500hPa AS DOUBLE)  AS wind500_dir,
        TRY_CAST(cape                  AS DOUBLE)  AS cape_jkg,
        TRY_CAST(precipitation         AS DOUBLE)  AS precip_mm,
        TRY_CAST(temperature_2m        AS DOUBLE)  AS temp_c,
        TRY_CAST(freezing_level_height AS DOUBLE)  AS freezing_level_m
    FROM {{ source('hrrr', 'hourly') }}
)
SELECT
    * EXCLUDE (wind10_dir, wind500_dir),
    -wind10_ms  * sin(radians(wind10_dir))   AS u10,
    -wind10_ms  * cos(radians(wind10_dir))   AS v10,
    -wind500_ms * sin(radians(wind500_dir))  AS u500,
    -wind500_ms * cos(radians(wind500_dir))  AS v500
FROM typed
