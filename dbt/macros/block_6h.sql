{#
  Start of the 6-hour block a timestamp falls in: 00, 06, 12 or 18 UTC.
  The modeling unit, as in weathernext-outage-forecasting:

      {{ block_6h('run_start_time') }} AS block_start
#}
{% macro block_6h(column) -%}
    (date_trunc('day', {{ column }}) + to_hours(6 * (hour({{ column }}) // 6)))
{%- endmacro %}
