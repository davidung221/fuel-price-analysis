{#
  By default dbt joins dataset names together (e.g. "staging_reporting").
  This makes each model go to exactly the dataset set in dbt_project.yml:
  staging models -> staging, reporting models -> reporting.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
