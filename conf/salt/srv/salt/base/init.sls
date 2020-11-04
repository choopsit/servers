{% set mypkg_list = pillar.get("packages", []) %}

{% for mypkg in mypkg_list %}
{{ mypkg }}:
  pkg.installed

{% endfor %}

/etc/ssh/sshd_config:
  file.managed:
    - source: salt://conf/ssh/sshd_config
