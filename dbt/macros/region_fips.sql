{#
  County FIPS -> analysis region. St. Louis City (29510) and County (29189)
  become one region, because EAGLE-I filed the County's outages under the
  City's code from mid-2020 to 2024 (docs/data-notes.md). Every other county
  is its own region. Use it anywhere a county code enters the pipeline:

      {{ region_fips('fips_code') }} AS region_fips
#}
{% macro region_fips(column) -%}
    CASE WHEN {{ column }} IN ('29189', '29510') THEN '29189+29510' ELSE {{ column }} END
{%- endmacro %}
