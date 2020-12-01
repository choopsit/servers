{% set basepkgs = pillar.get('packages', []) %}
{% for mypkg in basepkgs %}
{{ mypkg }}:
  pkg.installed

{% endfor %}

'/root/.profile':
  file.managed:
    - source: salt://conf/bash/profile

'/root/.config/bash/bashrc':
  file.managed:
    - source: salt://conf/bash/bashrc_root
    - makedirs: True

'/root/.vim/vimrc':
  file.managed:
    - source: salt://conf/vim/vimrc
    - makedirs: True

'/etc/ssh/sshd_config':
  file.managed:
    - source: salt://conf/ssh/sshd_config

{% for user in salt['user.list_users'] %}
{% if salt['file.directory_exists' ]('/home/' ~ user) %}
'/home/{{ user }}/.profile':                                                                  
  file.managed:                                                                  
    - source: salt://conf/bash/profile
    - user: {{ user }}
    - group: {{ user }}

'/home/{{ user }}/.config/bash/bashrc':
  file.managed:
    - source: salt://conf/bash/bashrc_user
    - makedirs: True
    - user: {{ user }}
    - group: {{ user }}

'/home/{{ user }}/.vim/vimrc':
  file.managed:
    - source: salt://conf/vim/vimrc
    - makedirs: True
    - user: {{ user }}
    - group: {{ user }}

{% endif %}
{% endfor %}
