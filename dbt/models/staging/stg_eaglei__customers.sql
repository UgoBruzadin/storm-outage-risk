-- Customers per county (EAGLE-I's modeled customer count, MCC.csv).
-- Two traps: FIPS is stored as text without the leading zero ('1001' is
-- Alabama's 01001), and the last row is 'Grand Total', not a county.

SELECT
    lpad(County_FIPS, 5, '0')  AS fips_code,
    Customers                  AS customers
FROM {{ source('eaglei', 'modeled_customers') }}
WHERE County_FIPS <> 'Grand Total'
