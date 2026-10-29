-- Every hour from EAGLE-I's first snapshot to its last, with how many national
-- snapshots EAGLE-I recorded in it: the hourly heartbeat (4 when complete, one
-- every 15 min). Same rule as int_eaglei__blocks_6h: an hour is covered when at
-- least half its snapshots exist.

WITH snapshot_times AS (
    SELECT DISTINCT snapshot_time
    FROM {{ ref('stg_eaglei__outages') }}
),
counts AS (
    SELECT date_trunc('hour', snapshot_time) AS hour, count(*) AS n_snapshots
    FROM snapshot_times
    GROUP BY 1
),
all_hours AS (
    SELECT unnest(generate_series(
        (SELECT min(hour) FROM counts),
        (SELECT max(hour) FROM counts),
        INTERVAL 1 HOUR)) AS hour
)
SELECT
    h.hour,
    coalesce(c.n_snapshots, 0)                  AS n_snapshots,
    coalesce(c.n_snapshots, 0) >= 2             AS eaglei_ok
FROM all_hours AS h
LEFT JOIN counts AS c USING (hour)
