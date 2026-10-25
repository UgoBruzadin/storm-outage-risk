-- NOAA Storm Events reports for Missouri (29) and Illinois (17), times in UTC.
--
-- Times come as local *standard* time all year, with the offset in
-- CZ_TIMEZONE ('CST-6' = UTC−6), so UTC = local − offset. BEGIN_DATE_TIME
-- has a 2-digit year ('01-JUL-23 23:33:00'), so we rebuild the timestamp from
-- the unambiguous BEGIN_YEARMONTH / BEGIN_DAY / BEGIN_TIME (hhmm) fields.
--
-- CZ_TYPE 'C' = county (thunderstorm wind, hail, tornado, floods);
-- 'Z' = NWS forecast zone (winter storms, ice, high wind) — mapped to
-- counties downstream with the zone–county file.

WITH parsed AS (
    SELECT
        EVENT_ID                                                      AS event_id,
        EPISODE_ID                                                    AS episode_id,
        EVENT_TYPE                                                    AS event_type,
        CZ_TYPE                                                       AS cz_type,
        lpad(STATE_FIPS, 2, '0')                                      AS state_fips,
        lpad(CZ_FIPS, 3, '0')                                         AS cz_fips,
        CZ_NAME                                                       AS cz_name,
        STATE                                                         AS state,
        strptime(BEGIN_YEARMONTH || lpad(BEGIN_DAY, 2, '0') || lpad(BEGIN_TIME, 4, '0'), '%Y%m%d%H%M') AS begin_local,
        strptime(END_YEARMONTH   || lpad(END_DAY, 2, '0')   || lpad(END_TIME, 4, '0'),   '%Y%m%d%H%M') AS end_local,
        CAST(regexp_extract(CZ_TIMEZONE, '-?\d+$') AS INT)            AS utc_offset_h,
        TRY_CAST(MAGNITUDE AS DOUBLE)                                 AS magnitude,
        MAGNITUDE_TYPE                                                AS magnitude_type
    FROM {{ source('storm_events', 'details') }}
    WHERE STATE_FIPS IN ('17', '29')
)
SELECT
    * EXCLUDE (begin_local, end_local, utc_offset_h),
    begin_local - to_hours(utc_offset_h)  AS begin_utc,
    end_local   - to_hours(utc_offset_h)  AS end_utc
FROM parsed
