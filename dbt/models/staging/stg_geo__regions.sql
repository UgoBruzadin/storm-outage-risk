-- The study-area regions (counties, with St. Louis City + County
-- merged), from the Census boundary file, plus their 2021 tree canopy.
-- Sources are read as text (see _sources.yml), so numbers are cast here.

SELECT
    r.region_fips,
    r.region,
    r.state,
    CAST(r.land_m2 AS DOUBLE) / 1e6            AS land_km2,
    CAST(r.lat AS DOUBLE)                      AS lat,
    CAST(r.lon AS DOUBLE)                      AS lon,
    CAST(t.canopy_mean_pct AS DOUBLE)          AS canopy_mean_pct,
    CAST(t.canopy_dense_share AS DOUBLE)       AS canopy_dense_share
FROM {{ source('geo', 'regions') }} AS r
LEFT JOIN {{ source('geo', 'tree_canopy') }} AS t USING (region_fips)
