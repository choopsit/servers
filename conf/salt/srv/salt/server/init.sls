{% set srvpkgs = pillar.get("specific_packages", []) %}
{% for mypkg in srvpkgs %}
{{ mypkg }}:
  pkg.installed

{% endfor %}
