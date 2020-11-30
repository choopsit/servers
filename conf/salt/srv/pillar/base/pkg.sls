{% if grains['kernel'] == 'Linux' %}
packages:
  - vim
  - ssh
  - git
  - curl
  - rsync
  - tree
  - htop

{% endif %}
