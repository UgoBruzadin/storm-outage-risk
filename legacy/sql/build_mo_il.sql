-- =============================================================================
-- build_mo_il.sql
-- Outages for every county in Missouri and Illinois (216 regions), so we can
-- compare places: which counties lose power most, and recover worst?
--
-- Run after merge_all.sql (it reuses stg.eaglei_snapshots, the national
-- "heartbeat"), from the repository root:
--     pixi run build
--
-- Same rules as merge_all.sql — see the comments there for the why:
--   * 2023's count column is "sum", so coalesce(customers_out, "sum")
--   * St. Louis City (29510) + County (29189) are one region, because
--     EAGLE-I filed the County's outages under the City from mid-2020 to 2024
--   * no row = 0 customers out, but only when EAGLE-I was running
--
-- Tables (all in schema mo_il):
--   mo_il.regions       216 rows: FIPS -> region, state, customers
--   mo_il.outage_hourly one row per region per hour WITH an outage (sparse)
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS mo_il;


-- -----------------------------------------------------------------------------
-- 1. Snapshots: every 15-minute reading in MO + IL, regions merged
-- -----------------------------------------------------------------------------
-- Summed per snapshot right away: after the St. Louis merge a region can have
-- two rows per snapshot (City and County), and they must be added, not maxed.
-- This reads all 12 national files once (~10 s) and keeps ~16M rows.

CREATE OR REPLACE TABLE mo_il.snapshots AS
SELECT
    CASE WHEN fips_code IN ('29189', '29510') THEN '29189+29510'
         ELSE fips_code END                              AS fips_code,
    run_start_time,
    sum(coalesce(customers_out, "sum"))::BIGINT          AS customers_out
FROM read_csv('data/raw/eaglei/eaglei_outages_*.csv', union_by_name = true)
WHERE state IN ('Missouri', 'Illinois')
GROUP BY ALL;


-- -----------------------------------------------------------------------------
-- 2. Regions: names and customer counts
-- -----------------------------------------------------------------------------
-- County names come from EAGLE-I (latest name seen), customers from MCC.csv
-- (summed for the St. Louis region). lpad: MCC drops leading zeros.

CREATE OR REPLACE TABLE mo_il.regions AS
WITH seen AS (
    SELECT
        CASE WHEN fips_code IN ('29189', '29510') THEN '29189+29510'
             ELSE fips_code END                                         AS fips_code,
        CASE WHEN fips_code IN ('29189', '29510') THEN 'St. Louis City + County'
             ELSE county END                                            AS county,
        state,
        max(run_start_time)                                             AS last_seen
    FROM read_csv('data/raw/eaglei/eaglei_outages_*.csv', union_by_name = true)
    WHERE state IN ('Missouri', 'Illinois')
    GROUP BY ALL
),
names AS (
    -- arg_max(x, y): the x from the row with the largest y = the latest name
    SELECT fips_code, arg_max(county, last_seen) AS county, arg_max(state, last_seen) AS state
    FROM seen
    GROUP BY fips_code
),
customers AS (
    SELECT
        CASE WHEN lpad(County_FIPS, 5, '0') IN ('29189', '29510') THEN '29189+29510'
             ELSE lpad(County_FIPS, 5, '0') END                         AS fips_code,
        sum(Customers)::BIGINT                                          AS customers
    FROM read_csv('data/raw/eaglei/MCC.csv')
    WHERE County_FIPS <> 'Grand Total'
    GROUP BY 1
)
SELECT n.fips_code, n.county, n.state, c.customers
FROM names AS n
LEFT JOIN customers AS c USING (fips_code);


-- -----------------------------------------------------------------------------
-- 3. Hourly: worst snapshot per region per hour (only hours with an outage)
-- -----------------------------------------------------------------------------
-- Sparse on purpose: a full grid would be 216 x ~97,000 hours = 21M rows,
-- and the resilience measures only need the hours when something happened.
-- Hours missing here are 0 — unless EAGLE-I was down (no row in
-- stg.eaglei_snapshots), which matters when you count "time between outages".

CREATE OR REPLACE TABLE mo_il.outage_hourly AS
SELECT
    s.fips_code,
    date_trunc('hour', s.run_start_time)          AS hour,
    max(s.customers_out)                          AS peak_out,
    100.0 * max(s.customers_out) / r.customers    AS pct_out
FROM mo_il.snapshots AS s
JOIN mo_il.regions AS r USING (fips_code)
GROUP BY s.fips_code, hour, r.customers;


-- -----------------------------------------------------------------------------
-- Final check
-- -----------------------------------------------------------------------------
SELECT
    (SELECT count(*) FROM mo_il.regions)                                AS regions,
    (SELECT count(*) FROM mo_il.regions WHERE customers IS NULL)        AS regions_without_customers,
    (SELECT count(*) FROM mo_il.outage_hourly)                          AS outage_hours,
    (SELECT min(hour) FROM mo_il.outage_hourly)                         AS first_hour,
    (SELECT max(hour) FROM mo_il.outage_hourly)                         AS last_hour;
