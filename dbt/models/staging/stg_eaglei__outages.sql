-- EAGLE-I snapshots, national, all years — one row per county per 15-minute
-- snapshot with at least one customer out. A view: nothing is copied, the
-- CSVs are read when a downstream model needs them.
--
-- The yearly files don't share columns: 2023 calls the count "sum", 2024 adds
-- total_customers. union_by_name lines them up; coalesce merges the counts so
-- 2023 isn't silently all NULL. Blank counts stay NULL (= unknown, not 0).
--
-- snapshot_time = run_start_time rounded down to the 15-minute grid. In early
-- Sept 2025 every snapshot appears twice (e.g. 00:00:00 and 00:00:52), and a
-- few snapshots sit off the grid (:01, :16, :31, :35). Downstream models use
-- snapshot_time and keep one value per county per slot, so nothing is
-- double-counted.

SELECT
    fips_code,
    county,
    state,
    run_start_time,
    time_bucket(INTERVAL 15 MINUTE, run_start_time)  AS snapshot_time,
    coalesce(customers_out, "sum")                   AS customers_out
FROM {{ source('eaglei', 'outages') }}
