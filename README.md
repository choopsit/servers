# servers

## Python scripts to deploy servers

### \_myhelpers\_.py
Usefull functions for 'choopsit/servers'

Usage:
    
    ./\_myhelpers\_.py [OPTION]
      
Options:
    
    -h,--help: Print this help

### \_serverbase\_.py:
Install Debian server base

Usage:

    './\_serverbase\_.py [OPTION]' as root or using 'sudo'

Options:

    -h,--help: Print this help

### dhcp.py:
Install Debian DHCP server

Usage:

    './dhcp.py [OPTION]' as root or using 'sudo'

Options:

    -h,--help: Print this help

### pxe.py:
Install Debian PXE Boot server

Usage:

    './pxe.py [OPTION]' as root or using 'sudo'

Options:

    -h,--help: Print this help

### samba4ad.py:
Install an Active Directory Domain Controller on Debian

Usage:

    './samba4ad.py [OPTION]' as root or using 'sudo'

Options:

    -h,--help: Print this help

### saltmaster.py:
Install a Debian SaltStack master

Usage:

    './saltmaster.py [OPTION]' as root or using 'sudo'

Options:

    -h,--help: Print this help

### saltminion.py:
Install SaltStack minion on Debian

Usage:

    './saltminion.py [OPTION]' as root or using 'sudo'

Options:

    -h,--help: Print this help

### localrepo.py:
Install a local Debian and/or Ubuntu repo on Debian

Usage:

    './localrepo.py [OPTION]' as root or using 'sudo'

Options:

    -h,--help: Print this help

### nextcloud.py:
Install Debian Nextcloud server

Usage:

    './nextcloud.py [OPTION]' as root or using 'sudo'

Options:

    -h,--help: Print this help

## Test Platform:

### {subnet}.1  dhcp.{domain}
dhcp.py _(plage dhcp: {subnet}.100-{subnet}.199)_ + pxe.py

### {subnet}.2  dc.{domain}
samba4ad.py

### {subnet}.3  salt.{domain}
saltmaster.py

### {subnet}.4  apps.{domain}
localrepo.py

### {subnet}.5  web.{domain}:

