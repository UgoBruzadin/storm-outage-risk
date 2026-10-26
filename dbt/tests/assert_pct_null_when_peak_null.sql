-- Regression test for a real bug: least(100, NULL) returns 100 in DuckDB, so
-- blank outage counts once became "100% of customers out" (tens of
-- thousands of fake events). A percentage must never exist without a count.

SELECT region_fips, block_start, peak_out, peak_pct_out
FROM {{ ref('mart_study__region_6h') }}
WHERE peak_out IS NULL AND peak_pct_out IS NOT NULL
