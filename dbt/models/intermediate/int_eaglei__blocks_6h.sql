-- Every 6-hour block (00/06/12/18 UTC) from EAGLE-I's first snapshot to its
-- last, with how many national snapshots EAGLE-I recorded in it — the
-- "heartbeat". A full block has 24 (every 15 min); when EAGLE-I was down,
-- fewer or none. Outage-free hours look the same as "EAGLE-I down" in a
-- single county, so we judge coverage from the whole country: someone in
-- the U.S. is always without power.

WITH snapshot_times AS (
    SELECT DISTINCT snapshot_time                 -- on the 15-min grid: duplicates collapse
    FROM {{ ref('stg_eaglei__outages') }}
),
counts AS (
    SELECT {{ block_6h('snapshot_time') }} AS block_start, count(*) AS n_snapshots
    FROM snapshot_times
    GROUP BY 1
),
all_blocks AS (
    SELECT unnest(generate_series(
        (SELECT min(block_start) FROM counts),
        (SELECT max(block_start) FROM counts),
        INTERVAL 6 HOUR)) AS block_start
)
SELECT
    b.block_start,
    coalesce(c.n_snapshots, 0)                  AS n_snapshots,
    coalesce(c.n_snapshots, 0) >= 12            AS eaglei_ok    -- at least half the snapshots
FROM all_blocks AS b
LEFT JOIN counts AS c USING (block_start)
