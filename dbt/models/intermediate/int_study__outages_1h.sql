-- Peak customers out per region per hour, study area: hours with an outage row
-- only (the grid in mart_study__region_1h fills in the zeros). The same steps as
-- int_study__outages_6h, at hourly grain: one value per county per 15-min slot
-- (the larger of duplicate snapshots), counties added into regions per slot, then
-- the worst slot in the hour.

WITH per_county_slot AS (
    SELECT fips_code, snapshot_time, max(customers_out) AS customers_out
    FROM {{ ref('stg_eaglei__outages') }}
    WHERE left(fips_code, 2) IN (SELECT state_fips FROM {{ ref('study_states') }})
    GROUP BY ALL
),
per_region_slot AS (
    SELECT
        {{ region_fips('fips_code') }}      AS region_fips,
        snapshot_time,
        sum(customers_out)                  AS customers_out
    FROM per_county_slot
    GROUP BY ALL
)
SELECT
    region_fips,
    date_trunc('hour', snapshot_time)       AS hour,
    max(customers_out)                      AS peak_out
FROM per_region_slot
GROUP BY ALL
