-- NWS forecast zone -> county, for the study states. One zone can cover several
-- counties (and a county can sit in several zones), so a zone event is
-- assigned to every county of its zone downstream.

SELECT DISTINCT
    state_zone          AS zone_id,     -- e.g. 'MO009'
    fips                AS fips_code    -- e.g. '29199'
FROM {{ source('storm_events', 'zone_county') }}
WHERE state IN (SELECT state_abbr FROM {{ ref('study_states') }})
