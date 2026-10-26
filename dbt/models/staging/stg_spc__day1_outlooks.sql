-- SPC Day 1 convective outlooks per region. One row per outlook product x region.
--
-- Products are issued five times a day (cycles 06, 13, 16, 20, 01 UTC) for the
-- 12Z -> 12Z convective day: issued_utc is when forecasters sent it, valid_from /
-- valid_to the period it covers.
--   spc_cat        categorical risk: 0 none, 1 TSTM, 2 MRGL, 3 SLGT, 4 ENH, 5 MDT, 6 HIGH
--   spc_*_prob     probability of that hazard within 25 miles of a point (0-0.60)

SELECT
    strptime(prodiss, '%Y%m%d%H%M')                  AS issued_utc,
    strptime(issue, '%Y%m%d%H%M')                    AS valid_from,
    strptime(expire, '%Y%m%d%H%M')                   AS valid_to,
    CAST(cycle AS INTEGER)                           AS cycle,
    region_fips,
    CAST(CAST(spc_cat AS DOUBLE) AS INTEGER)         AS spc_cat,
    CAST(spc_wind_prob AS DOUBLE)                    AS spc_wind_prob,
    CAST(spc_tor_prob AS DOUBLE)                     AS spc_tor_prob,
    CAST(spc_hail_prob AS DOUBLE)                    AS spc_hail_prob
FROM {{ source('nws', 'spc_day1') }}
