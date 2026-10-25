-- One row per MO+IL analysis region with everything we know about the place:
-- size (customers, land), trees (canopy), and the built environment (ACS).
--
-- Counties come from the customer file, so all 217 MO+IL counties are here
-- even if one never had an outage. Merging St. Louis City + County means
-- adding counts up; the median year built can't be merged exactly, so the
-- region's value is the housing-weighted average of the two county medians.

WITH counties AS (
    SELECT
        c.fips_code,
        {{ region_fips('c.fips_code') }}      AS region_fips,
        c.customers,
        a.population,
        a.housing_units,
        a.homes_pre1960,
        a.homes_total,
        a.median_year_built
    FROM {{ ref('stg_eaglei__customers') }} AS c
    LEFT JOIN {{ ref('stg_acs__housing') }} AS a USING (fips_code)
    WHERE c.fips_code LIKE '17%' OR c.fips_code LIKE '29%'
),
by_region AS (
    SELECT
        region_fips,
        count(*)                                                    AS n_counties,
        sum(customers)                                              AS customers,
        sum(population)                                             AS population,
        sum(housing_units)                                          AS housing_units,
        sum(homes_pre1960) / sum(homes_total)                       AS share_homes_pre1960,
        round(sum(median_year_built * housing_units) / sum(housing_units)) AS median_year_built
    FROM counties
    GROUP BY region_fips
)
SELECT
    g.region_fips,
    g.region,
    g.state,
    g.lat,
    g.lon,
    g.land_km2,
    r.n_counties,
    r.customers,
    r.population,
    r.housing_units,
    r.housing_units / g.land_km2      AS housing_per_km2,
    r.share_homes_pre1960,
    r.median_year_built,
    g.canopy_mean_pct,
    g.canopy_dense_share
FROM {{ ref('stg_geo__regions') }} AS g
JOIN by_region AS r USING (region_fips)
