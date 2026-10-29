-- Was EAGLE-I actually tracking each region in each year? The national heartbeat can't
-- tell: it says the tracker was running somewhere, not that this region's utility was
-- reporting. A tracked region almost always has someone out, so the share of hours with
-- anyone out is a coverage signal: Jefferson Co., MO shows 0.3% in 2018 and 7% in 2019,
-- then 54-65% every year from 2020; Webster Co., MO 2-6% in 2020-2021, then 25-60%.
--
-- tracked = the region-year's share is at least a fifth of the region's own typical
-- share (its 75th-percentile year: a median is pulled down when several years are missing,
-- as for McDonald Co., MO, 2018-2022). Untracked region-years are left out of
-- training and scoring: their calm hours are missing data, not calm.

WITH yearly AS (
    SELECT region_fips, year(hour) AS year, avg((pct_out > 0)::INT) AS share_hours_any_out, count(pct_out) AS known_hours
    FROM {{ ref('mart_study__region_1h') }}
    GROUP BY ALL
),
typical AS (
    SELECT region_fips, quantile_cont(share_hours_any_out, 0.75) AS typical_share FROM yearly GROUP BY 1
)
SELECT
    y.*,
    t.typical_share,
    y.share_hours_any_out >= 0.2 * t.typical_share      AS tracked
FROM yearly AS y
JOIN typical AS t USING (region_fips)
