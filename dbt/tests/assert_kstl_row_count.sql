-- A "singular" test: a query that returns rows only when something is wrong.
-- The old check comment said: 102,035 rows (2014 – 2025-08-27). Re-downloading
-- NOAA can add a few rows, so allow a range instead of an exact number.

SELECT count(*) AS n_rows
FROM {{ ref('stg_noaa__kstl_hourly') }}
HAVING count(*) NOT BETWEEN 100000 AND 110000
