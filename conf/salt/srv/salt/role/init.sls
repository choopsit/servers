role:
  grains.present:
    {% if grains['id'].lower().startswith('ws') %}
    - value: workstation
    {% else %}
    - value: server
    {% endif %}
