-- NOAA Storm Events reports per region per 6-hour block: what forecasters
-- and spotters saw, independently of the model's weather inputs. Useful to
-- define "a storm hit this county", and to check the model on storm blocks.
--
-- County events (CZ_TYPE 'C') carry the county FIPS directly; zone events
-- ('Z': winter storm, ice storm, high wind...) are spread to every county in
-- the zone. An event that spans several blocks counts in each of them.
-- Wind magnitudes are knots (x 0.514 = m/s), hail sizes inches.

WITH events AS (
    SELECT
        e.state_fips || e.cz_fips                       AS fips_code,
        e.*
    FROM {{ ref('stg_noaa__storm_events') }} AS e
    WHERE e.cz_type = 'C'

    UNION ALL BY NAME

    SELECT
        z.fips_code,
        e.*
    FROM {{ ref('stg_noaa__storm_events') }} AS e
    JOIN {{ ref('stg_noaa__zone_county') }} AS z
      ON z.zone_id = CASE e.state_fips WHEN '29' THEN 'MO' WHEN '17' THEN 'IL' END || e.cz_fips
    WHERE e.cz_type = 'Z'
),
by_block AS (
    SELECT
        {{ region_fips('fips_code') }}                                   AS region_fips,
        unnest(generate_series({{ block_6h('begin_utc') }},
                               {{ block_6h('end_utc') }},
                               INTERVAL 6 HOUR))                         AS block_start,
        event_id,
        event_type,
        magnitude
    FROM events
)
SELECT
    region_fips,
    block_start,
    count(DISTINCT event_id)                                                          AS n_reports,
    count(DISTINCT event_id) FILTER (WHERE event_type = 'Thunderstorm Wind')          AS n_tstm_wind,
    max(magnitude)           FILTER (WHERE event_type = 'Thunderstorm Wind')          AS max_tstm_wind_kt,
    count(DISTINCT event_id) FILTER (WHERE event_type = 'Hail')                       AS n_hail,
    max(magnitude)           FILTER (WHERE event_type = 'Hail')                       AS max_hail_in,
    count(DISTINCT event_id) FILTER (WHERE event_type = 'Tornado')                    AS n_tornado,
    count(DISTINCT event_id) FILTER (WHERE event_type IN ('High Wind', 'Strong Wind')) AS n_high_wind,
    count(DISTINCT event_id) FILTER (WHERE event_type IN ('Ice Storm', 'Winter Storm', 'Heavy Snow',
                                                           'Blizzard', 'Sleet'))       AS n_winter
FROM by_block
GROUP BY ALL
