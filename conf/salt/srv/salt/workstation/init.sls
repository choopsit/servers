functions:
  grains.present

{% set wsfunctions = grains.get("functions", []) %}
{% if wsfunctions != [] %}
include:
  {% for myfunction in wsfunctions %}
  - workstation.{{ myfunction }}
  {% endfor %}

{% endif %}
