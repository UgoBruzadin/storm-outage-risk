-- Census ACS 2020–2024 5-year estimates per county, MO + IL.
-- GEO_ID for a county is '0500000US' + 5-digit FIPS. B25034 counts homes by
-- decade built: E009 = 1950s, E010 = 1940s, E011 = 1939 or earlier.

WITH counties AS (
    SELECT GEO_ID, substr(GEO_ID, 10, 5) AS fips_code
    FROM {{ source('acs', 'year_built') }}
    WHERE GEO_ID LIKE '0500000US17%' OR GEO_ID LIKE '0500000US29%'
)
SELECT
    c.fips_code,
    p.B01003_E001                                       AS population,
    h.B25001_E001                                       AS housing_units,
    y.B25034_E009 + y.B25034_E010 + y.B25034_E011       AS homes_pre1960,
    y.B25034_E001                                       AS homes_total,
    TRY_CAST(m.B25035_E001 AS INT)                      AS median_year_built
FROM counties AS c
JOIN {{ source('acs', 'year_built') }}        AS y USING (GEO_ID)
JOIN {{ source('acs', 'median_year_built') }} AS m USING (GEO_ID)
JOIN {{ source('acs', 'population') }}        AS p USING (GEO_ID)
JOIN {{ source('acs', 'housing_units') }}     AS h USING (GEO_ID)
