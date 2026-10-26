-- NWS warnings for the study states, one row per warning per county or zone.
--
-- A warning is identified by office + phenomenon + event number + year; the UGC
-- says where: 'MOC163' = Missouri county 163, 'MOZ009' = Missouri forecast zone 9.
-- The row carries the warning's final status and its issue -> expire window (UTC).

SELECT
    wfo,
    phenomena,                                       -- SV, TO, HW, IS, WS, BZ
    CAST(eventid AS INTEGER)                        AS event_id,
    CAST(vtec_year AS INTEGER)                      AS vtec_year,
    status,
    left(ugc, 2)                                    AS state_abbr,
    substr(ugc, 3, 1)                               AS ugc_type,      -- C = county, Z = zone
    right(ugc, 3)                                   AS ugc_number,
    CAST(utc_issue AS TIMESTAMP)                    AS issue_utc,
    CAST(utc_expire AS TIMESTAMP)                   AS expire_utc
FROM {{ source('nws', 'warnings') }}
WHERE significance = 'W'
