base:
  '*':
    - base.pkg

  'G@role:server':
    - server.{{ grains['id'].split('.')[0] }}
