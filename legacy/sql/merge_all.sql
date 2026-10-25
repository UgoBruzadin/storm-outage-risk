-- =============================================================================
-- merge_all.sql
-- Build an hourly table of power outages + weather for the St. Louis metro,
-- Nov 2014 – Aug 2025 (EAGLE-I starts 2014-11-01; NOAA weather currently
-- ends 2025-08-27, and the grid stops wherever the shorter dataset ends).
--
-- Run from the repository root (paths below are relative to it):
--     pixi run build
--
-- Every table is CREATE OR REPLACE, so you can re-run the whole file any time
-- and get the same result. Never edit tables by hand — change this file.
--
-- Layers:
--   raw.*  data exactly as it came from the files (only filtered, never fixed)
--   stg.*  cleaned, reshaped, joined — what you analyze
--
-- Final output: stg.merged_hourly — one row per county per hour
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS stg;

-- -----------------------------------------------------------------------------
-- 1. RAW: EAGLE-I outages, filtered to the 8 St. Louis metro counties
-- -----------------------------------------------------------------------------
-- One row = one county at one 15-minute snapshot with ≥1 customer out.
-- IMPORTANT: no row means zero customers out (EAGLE-I doesn't record zeros).
-- Timestamps are UTC.
--
-- Two different places are both called "St. Louis", so we rename them here,
-- during the load, so the fix is reapplied every time the table is rebuilt.
--
-- The yearly files don't all have the same columns:
--   2023 calls the outage count "sum" instead of customers_out
--   2024 has an extra total_customers column
-- union_by_name lines columns up by name; coalesce merges the two count
-- columns, so 2023 isn't silently all NULL (= a year with "no outages").
--
-- NOTE: EAGLE-I's utility coverage grew over time. coverage_history.csv shows
-- Missouri at ~79% of customers tracked in 2018 and ~95% from 2019 on (Illinois
-- ~91% -> 97%). Outage counts before 2019 are undercounted, so an upward trend
-- is partly coverage, not weather. Decide on training years before modeling.

CREATE OR REPLACE TABLE raw.eaglei_outages AS
SELECT * EXCLUDE ("sum", total_customers) REPLACE (
    coalesce(customers_out, "sum") AS customers_out,
    CASE fips_code
        WHEN '29189' THEN 'St. Louis County'
        WHEN '29510' THEN 'St. Louis City'
        ELSE county
    END AS county
)
FROM read_csv('data/raw/eaglei/eaglei_outages_*.csv', filename = true, union_by_name = true)
WHERE fips_code IN (
    '29189',  -- St. Louis County, MO
    '29510',  -- St. Louis City, MO
    '29183',  -- St. Charles, MO
    '29099',  -- Jefferson, MO
    '29071',  -- Franklin, MO
    '17119',  -- Madison, IL
    '17163',  -- St. Clair, IL
    '17133'   -- Monroe, IL
);
-- Check: 1,406,194 rows (16,837 of them have a blank customers_out)


-- -----------------------------------------------------------------------------
-- 2. RAW: NOAA hourly weather at St. Louis Lambert airport (KSTL)
-- -----------------------------------------------------------------------------
-- all_varchar = true: NOAA packs several values into one text field
-- (e.g. TMP = '+0039,1'), so we load everything as text and unpack in step 3.
-- union_by_name: the optional columns (GA4, AX4, ...) vary from year to year.

CREATE OR REPLACE TABLE raw.noaa_hourly AS
SELECT *
FROM read_csv('data/raw/noaa/noaa_KSTL_*.csv', all_varchar = true, union_by_name = true);
-- Check: 151,666 rows (2025 is short: NOAA's file ends 2025-08-27)


-- -----------------------------------------------------------------------------
-- 3. STG: weather, one row per hour
-- -----------------------------------------------------------------------------
-- Unpacking pattern, read inside-out:
--   split_part(TMP, ',', 1)   take piece 1 before the comma   '+0039'
--   nullif(..., '+9999')      NOAA's "missing" code -> NULL
--   ::INT / 10.0              text -> number, NOAA stores values x10   3.9
--
-- Timing: the regular report (FM-15) comes at :51. We add 9 minutes so the
-- 10:51 report is labeled 11:00 = "weather going into hour 11". That way an
-- outage is only ever paired with weather measured BEFORE it (no leakage).
--
-- QUALIFY keeps only the earliest report per hour: a few hours have a second
-- FM-15 (e.g. 08:50 and 08:51), which would otherwise duplicate rows in joins.
--
-- Gusts: airports only report a gust when the wind is gusty, so ~86% of hours
-- have none. Here NULL means "no gust", not "unknown" — so we fall back to the
-- steady wind speed. (Compare peak_out in step 6, where NULL really is unknown.)
--
-- Thunder: the coded present-weather field (MW1) almost never records storms
-- at KSTL, but the original METAR text in REM does: 'TS', '-TSRA', 'VCTS'
-- (in the vicinity), or remarks like 'TSB28E51' (began :28, ended :51).
-- The regex looks for TS at the start of a word, optionally after + - or VC.
-- The report describes the hour before its label, so this is past-only info.

CREATE OR REPLACE TABLE stg.weather_hourly AS
SELECT
    date_trunc('hour', CAST("DATE" AS TIMESTAMP) + INTERVAL 9 MINUTE)  AS hour,
    nullif(split_part(TMP, ',', 1), '+9999')::INT / 10.0                AS temp_c,
    nullif(split_part(WND, ',', 4), '9999')::INT / 10.0                 AS wind_ms,    -- x 2.237 = mph
    coalesce(
        nullif(split_part(OC1, ',', 1), '9999')::INT / 10.0,                           -- reported gust
        nullif(split_part(WND, ',', 4), '9999')::INT / 10.0                            -- else steady wind
    )                                                                   AS gust_ms,
    CASE WHEN split_part(AA1, ',', 1) = '01'                                           -- keep 1-hour totals only
         THEN nullif(split_part(AA1, ',', 2), '9999')::INT / 10.0
    END                                                                 AS precip_mm,
    coalesce(regexp_matches(REM, ' (\+|-|VC)?TS'), false)               AS thunder     -- storm in the last hour
FROM raw.noaa_hourly
WHERE REPORT_TYPE = 'FM-15'   -- regular hourly report; skips daily summaries (SOD) etc.
QUALIFY row_number() OVER (PARTITION BY hour ORDER BY "DATE") = 1;
-- Check: 102,035 rows, count(*) = count(DISTINCT hour), 2,084 thunder hours

-- SUGGESTION: more weather features you could unpack the same way:
--   dewpoint_c    DEW, piece 1, missing '+9999'  -> humidity, fog, icing
--   pressure_hpa  SLP, piece 1, missing '99999'  -> sudden drops = storms
-- SUGGESTION: an ice flag — cold + wet is a classic outage cause:
--   (temp_c <= 0 AND precip_mm > 0) AS icing_risk


-- -----------------------------------------------------------------------------
-- 4. STG: outages, one row per region per hour
-- -----------------------------------------------------------------------------
-- Regions: from mid-2020 through 2024, EAGLE-I files St. Louis County's
-- outages under St. Louis City's FIPS code (29510): the County shows 0
-- outages for 2022–2024 (impossible for ~594k customers) while the City's
-- average jumps ~20x; in 2025 the County comes back. We can't split them
-- apart reliably, so we treat City + County as one region everywhere.
-- stg.regions maps each county FIPS to its region (the other 6 map to
-- themselves). Every later step works on regions instead of counties.

CREATE OR REPLACE TABLE stg.regions AS
SELECT DISTINCT
    fips_code,
    CASE WHEN fips_code IN ('29189', '29510') THEN '29189+29510'
         ELSE fips_code END                                AS region_fips,
    CASE WHEN fips_code IN ('29189', '29510') THEN 'St. Louis City + County'
         ELSE county END                                   AS region,
    state
FROM raw.eaglei_outages;
-- Check: 8 rows (8 counties -> 7 regions)

-- Squash the four 15-minute snapshots into one number: the worst moment.
-- Two steps, because a region can now have 2 rows per snapshot (City and
-- County, e.g. in 2025): first ADD them up per snapshot, then take the max
-- over the hour. (max first would only count the bigger of the two.)
-- No +9 minutes here: snapshots at :00/:15/:30/:45 already sit in their hour.
-- sum()/max() skip blank snapshots; if ALL of an hour's snapshots are blank,
-- peak_out is NULL (unknown) — step 6 keeps it that way.

CREATE OR REPLACE TABLE stg.outage_hourly AS
WITH per_snapshot AS (
    SELECT
        r.region_fips,
        r.region,
        e.run_start_time,
        sum(e.customers_out)::BIGINT  AS customers_out   -- ::BIGINT: sum() returns a 128-bit int
    FROM raw.eaglei_outages AS e
    JOIN stg.regions AS r USING (fips_code)
    GROUP BY ALL
)
SELECT
    region_fips                         AS fips_code,   -- keep the old column names
    region                              AS county,      -- so steps 5–6 don't change
    date_trunc('hour', run_start_time)  AS hour,
    max(customers_out)                  AS peak_out
FROM per_snapshot
GROUP BY ALL;
-- Check: 364,944 rows

-- SUGGESTION: other ways to summarize an hour, each answers a different question:
--   avg(customers_out)   typical level during the hour
--   count(*)             how many of the 4 snapshots had an outage (persistence)


-- -----------------------------------------------------------------------------
-- 5. STG: the grid — every region x every hour
-- -----------------------------------------------------------------------------
-- Without this, hours with no outage simply don't exist in the data, and a
-- model would never see "windy hour, nothing happened".
--
-- customers comes from MCC.csv (EAGLE-I's modeled customer count per county),
-- so step 6 can express outages as a percentage. Two traps in that file:
--   County_FIPS is text and drops leading zeros (Alabama = '1001'), so we
--   lpad it to 5 characters; and its last row is 'Grand Total', not a county
--   (it never matches a real FIPS code, so the join ignores it).
-- Customers are added up per region (St. Louis City + County = 701,367).

CREATE OR REPLACE TABLE stg.counties AS
SELECT
    r.region_fips      AS fips_code,
    r.region           AS county,
    r.state,
    sum(m.Customers)::BIGINT  AS customers
FROM stg.regions AS r
LEFT JOIN read_csv('data/raw/eaglei/MCC.csv') AS m
       ON lpad(m.County_FIPS, 5, '0') = r.fips_code
GROUP BY ALL;
-- Check: 7 regions, none with NULL customers (Monroe = 15,588)

CREATE OR REPLACE TABLE stg.hours AS
SELECT unnest(generate_series(
           (SELECT min(hour) FROM stg.outage_hourly),          -- start: first outage snapshot
           least(
               (SELECT max(hour) FROM stg.outage_hourly),      -- end: whichever dataset
               (SELECT max(hour) FROM stg.weather_hourly)      --      runs out first
           ),
           INTERVAL 1 HOUR)) AS hour;
-- Check: 94,850 rows (2014-11-01 04:00 -> 2025-08-27 05:00)

-- The "heartbeat": every hour in which EAGLE-I reported ANY outage, anywhere
-- in the US. Some county in the country always has someone out (~640 per
-- snapshot on average), so an hour with no rows at all nationwide means
-- EAGLE-I itself was down — not that the whole grid was perfect. We read the
-- national files (no county filter) because St. Louis alone can't tell
-- "power was fine" apart from "nobody was collecting".

CREATE OR REPLACE TABLE stg.eaglei_snapshots AS
SELECT DISTINCT
    date_trunc('hour', run_start_time)  AS hour
FROM read_csv('data/raw/eaglei/eaglei_outages_*.csv', union_by_name = true);
-- Check: 97,536 rows (356 grid hours are missing = EAGLE-I down)


-- -----------------------------------------------------------------------------
-- 6. STG: final merged table
-- -----------------------------------------------------------------------------
-- CROSS JOIN builds the grid (7 regions x 94,850 hours = 663,950 rows).
-- LEFT JOIN keeps every grid row and attaches outages/weather/heartbeat
-- when they exist; "no match" shows up as NULL in that table's columns.
--
-- peak_out has three cases, checked top to bottom:
--   no heartbeat (s.hour IS NULL)        -> NULL: EAGLE-I was down, unknown
--   no outage row (o.fips_code IS NULL)  -> 0: EAGLE-I was up, nothing out
--   otherwise                            -> the value (NULL if all blank)
-- We test o.fips_code (a join column), not o.peak_out: a NULL peak_out can
-- mean "no row" OR "row with blank value", and only the first one is a 0.
--
-- pct_out makes regions comparable: 9,000 out is ~59% of Monroe but ~1.3%
-- of St. Louis City + County. It needs the finished peak_out, so the grid is
-- built first in a WITH block (a named sub-query) and pct_out is added on top.
-- 100.0 (not 100) avoids integer division, which would round small outages
-- down to 0.
--
-- Weather joins on hour only: one airport for all 7 regions.

CREATE OR REPLACE TABLE stg.merged_hourly AS
WITH grid AS (
    SELECT
        c.fips_code,
        c.county,
        h.hour,
        CASE
            WHEN s.hour      IS NULL THEN NULL   -- EAGLE-I was down this hour -> unknown
            WHEN o.fips_code IS NULL THEN 0      -- EAGLE-I up, no row for this county -> 0
            ELSE o.peak_out                      -- real value (NULL if every snapshot was blank)
        END AS peak_out,
        c.customers,
        w.temp_c,
        w.wind_ms,
        w.gust_ms,
        w.precip_mm,
        w.thunder
    FROM stg.counties AS c
    CROSS JOIN stg.hours AS h
    LEFT JOIN stg.outage_hourly AS o
           ON o.fips_code = c.fips_code
          AND o.hour      = h.hour
    LEFT JOIN stg.weather_hourly AS w
           ON w.hour = h.hour
    LEFT JOIN stg.eaglei_snapshots AS s
           ON s.hour = h.hour
)
SELECT
    *,
    100.0 * peak_out / customers  AS pct_out
FROM grid;


-- -----------------------------------------------------------------------------
-- Final check — run this after the file finishes
-- -----------------------------------------------------------------------------
SELECT
    count(*)                                  AS total_rows,     -- 663,950
    count(*) FILTER (WHERE peak_out > 0)      AS outage_rows,    -- 343,735
    count(*) FILTER (WHERE peak_out = 0)      AS quiet_rows,     -- 313,942
    count(*) FILTER (WHERE peak_out IS NULL)  AS unknown_rows,   --   6,273
    round(max(pct_out), 2)                    AS max_pct_out,    --   58.76 (Monroe, 2025-03-15 tornado outbreak)
    count(*) FILTER (WHERE thunder) // 7      AS thunder_hours   --   1,912
FROM stg.merged_hourly;
