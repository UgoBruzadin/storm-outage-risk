-- Pairs of study-area regions near each other, from their centroids: the distance
-- (km, haversine) and the bearing from the region to its neighbour (degrees, 0 = north,
-- 90 = east). Two kinds, a pair can be both:
--   near     within 100 km in any direction
--   upwind   within 200 km and to the south-southwest through west-northwest
--            (bearing 200-290): where most storms in Missouri and Illinois arrive from,
--            so their weather and outages now are a sign of what is coming
-- Regions on the study area's western edge have no upwind neighbours (Kansas,
-- Oklahoma and Nebraska aren't in the study): their upwind features are NULL.

WITH r AS (
    SELECT region_fips, radians(lat) AS lat, radians(lon) AS lon FROM {{ ref('int_study__regions') }}
),
pairs AS (
    SELECT
        a.region_fips,
        b.region_fips                                                           AS neighbor_fips,
        2 * 6371 * asin(sqrt(sin((b.lat - a.lat) / 2) ^ 2
                             + cos(a.lat) * cos(b.lat) * sin((b.lon - a.lon) / 2) ^ 2)) AS distance_km,
        (degrees(atan2(sin(b.lon - a.lon) * cos(b.lat),
                       cos(a.lat) * sin(b.lat) - sin(a.lat) * cos(b.lat) * cos(b.lon - a.lon))) + 360) % 360
                                                                                AS bearing_deg
    FROM r AS a
    JOIN r AS b ON a.region_fips <> b.region_fips
)
SELECT
    *,
    distance_km <= 100                                                          AS is_near,
    distance_km <= 200 AND bearing_deg BETWEEN 200 AND 290                      AS is_upwind
FROM pairs
WHERE distance_km <= 100 OR (distance_km <= 200 AND bearing_deg BETWEEN 200 AND 290)
