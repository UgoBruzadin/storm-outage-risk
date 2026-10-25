-- Outages per region per 6-hour block, MO + IL — only blocks with at least
-- one outage row (the grid in the mart fills in the zeros).
--
-- Three steps:
--   1. one value per county per 15-min slot (EAGLE-I sometimes records a
--      snapshot twice — keep the larger, never add the copies)
--   2. ADD counties up into regions per slot (St. Louis City + County)
--   3. summarize the 6-hour block:
--        peak_out  worst slot in the block — the label
--        mean_out  average over the block's national snapshot slots, slots
--                  where this region had no row counting as 0
-- sum()/max() skip blank counts; a block where every count is blank gets
-- peak_out NULL (unknown).

WITH per_county_slot AS (
    SELECT fips_code, snapshot_time, max(customers_out) AS customers_out
    FROM {{ ref('stg_eaglei__outages') }}
    WHERE state IN ('Missouri', 'Illinois')
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
    o.region_fips,
    {{ block_6h('o.snapshot_time') }}                 AS block_start,
    max(o.customers_out)                              AS peak_out,
    sum(o.customers_out) / any_value(b.n_snapshots)   AS mean_out,
    count(*)                                          AS n_outage_snapshots
FROM per_region_slot AS o
JOIN {{ ref('int_eaglei__blocks_6h') }} AS b
  ON b.block_start = {{ block_6h('o.snapshot_time') }}
GROUP BY ALL
