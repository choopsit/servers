{% set basepkgs = pillar.get('packages', []) %}
{% for mypkg in basepkgs %}
{{ mypkg }}:
  pkg.installed

{% endfor %}

/etc/ssh/sshd_config:
  file.managed:
    - source: salt://conf/ssh/sshd_config
