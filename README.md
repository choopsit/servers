# servers

## Python scripts to deploy servers

### \_myhelpers\_.py
Usefull functions for 'choopsit/servers'
    
    ./_myhelpers_.py [-h]

### \_serverbase\_.py:
Install a Debian server base

    './_serverbase_.py [-h]' as root or using 'sudo'

### dhcp.py:
Install a DHCP server on Debian

    './dhcp.py [-h]' as root or using 'sudo'

### pxe.py:
Install a PXE Boot server on Debian

    './pxe.py [-h]' as root or using 'sudo'

### samba4ad.py:
Install an Active Directory Domain Controller on Debian

    './samba4ad.py [-h]' as root or using 'sudo'

### saltmaster.py:
Install a SaltStack master on Debian

    './saltmaster.py [-h]' as root or using 'sudo'

### saltminion.py:
Install SaltStack minion on Debian

    './saltminion.py [-h]' as root or using 'sudo'

### localrepo.py:
Install a local Debian and/or Ubuntu repo on Debian

    './localrepo.py [-h]' as root or using 'sudo'

### nextcloud.py:
Install a Nextcloud server on Debian

    './nextcloud.py [-h]' as root or using 'sudo'

## Test Platform:

### {subnet}.1  dhcp.{domain}:
dhcp.py _(plage dhcp: {subnet}.100-{subnet}.199)_

pxe.py

### {subnet}.2  dc.{domain}:
samba4ad.py

### {subnet}.3  salt.{domain}:
saltmaster.py

### {subnet}.4  apps.{domain}:
localrepo.py

### {subnet}.5  web.{domain}:

