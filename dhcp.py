#!/usr/bin/env python3

import sys
import re
import os
import _myhelpers_ as myh

__description__ = "Install Debian DHCP server"
__author__ = "Choops <choopsbd@gmail.com>"


def usage():
    myscript = f"{os.path.basename(sys.argv[0])}"
    print(f"{ci}{__description__}\nUsage{c0}:")
    print(f"  './{myscript} [OPTION]' as root or using 'sudo'")
    print(f"{ci}Options{c0}:")
    print(f"  -h,--help: Print this help")
    print()


def prerequisites():
    distro = ""
    codename = ""

    with open("/etc/os-release", "r") as f:
        for line in f:
            if line.startswith("ID="):
                distro = line.split("=")[1].rstrip()
            if line.startswith("VERSION_CODENAME="):
                codename = line.split("=")[1].rstrip()

    if distro != "debian":
        print(f"{error} OS is not Debian")
        exit(1)

    if os.getuid() != 0:
        print(f"{error} Need higher privileges")
        exit(1)

    if codename in olddebian:
        print(f"{error} '{codename}' is a too old Debian version")
        exit(1)

    if codename != debianstable:
        print(f"{warning} You are using a testing/unstable version of Debian.")
        okgo = input("Continue despite it could be unstable [y/N] ? ")
        if not re.match('^(y|yes)', okgo.lower()):
            exit(0)


def test_ip(ipaddr):
    ipend = ipaddr.split(".")[3]
    try:
        iend = int(ipend)
    except ValueError:
        print(f"{error} Invalid IP '{ipaddr}'")
        exit(1)

    if not 1 < istart < 254:
        print(f"{error} Invalid IP '{ipaddr}'")
        exit(1)

    return ipaddr


def set_dhcp(subnet):
    mystart = input(f"First IP of DHCP range ? {subnet}.")
    dhcpstart = test_ip(f"{subnet}.{mystart}")

    myend = input(f"Last IP of DHCP range ? {subnet}.")
    dhcpend = test_ip(f"{subnet}.{myend}")

    return dhcpstart, dhcpend


def set_pxe(subnet, srvip):
    pxeipend = input(f"IP of PXE server [default: '{srvip}']? {subent}.")
    pxeip = test_ip(f"{subnet}.{pxeipend}")
    if pxeip == "":
        pxeip = srvip

    return pxeip


def configure_server(domain, subnet, dhcpstart, dhcpend, pxeip, iface):
    print(f"{ci}Configuring server...{c0}")
    myh.common_config()

    dnssrv = myh.get_dns()
    gateway = myh.get_gw()

    dhcpconf = "/etc/dhcp/dhcpd.conf"
    if os.isfile(dhcpconf):
        os.rename(dhcpconf, f"{dhcpconf}.o")

    with open(dhcpconf, "w") as f:
        f.write("default-lease-time 600;\n")
        f.write("max-lease-time 7200;\n\n")
        f.write("allow booting;\n\n")
        f.write(f"subnet {subnet}.0 netmask 255.255.255.0 \{\n")
        f.write(f"    range {dhcpstart} {dhcpend};\n")
        f.write(f"    #option broadcast-address {subnet}.255;\n")
        f.write(f"    option routers {gateway};\n")
        f.write(f"    option domain-name-servers {dns};\n")
        f.write(f"    option domain-name \"{domain_name}\";\n")
        f.write(f"    next-server {pxeip};\n")
        f.write("    filename \"pxelinux.0\";\n")
        f.write("}\n\n")
        f.write("group {\n")
        f.write(f"    next-server {pxeip};\n")
        f.write("    host tftpclient {\n")
        f.write("        filename \"pxelinux.0\";\n")
        f.write("    }\n}\n")

    if subnet == "192.168.42":
        with open(dhcpconf, "a") as f:
            f.write("\nhost mrchat {\n")
            f.write("    hardware ethernet 6e:bc:7f:c4:34:0a;\n")
            f.write("    fixed-address 192.168.42.200;\n}\n")

    dhcpdef = "/etc/default/isc-dhcp-server"
    if os.isfile(dhcpdef):
        os.rename(dhcpdef, f"{dhcpdef}.o")

    with open(f"{dhcpdef}.o", "r") as oldf, open(dhcpdef,"w") as newf:
        for line in oldf:
            if line.statrtswith("INTERFACESv4="):
                newf.write(f"INTERFACESv4=\"{iface}\"\n")
            else:
                newf.write(line)

    service = "isc-dhcp-server"
    sysctl_cmds = ["daemon-reload", f"enable {service}", f"restart {service}"]
    for sysctl_cmd in sysctl_cmds:
        os.system(f"systemctl {sysctl_cmd}")


c0 = "\33[0m"
ce = "\33[31m"
cok = "\33[32m"
cw = "\33[33m"
ci = "\33[36m"

error = f"{ce}E{c0}:"
done = f"{cok}OK{c0}:"
warning = f"{cw}W{c0}:"

srcfolder = os.path.dirname(os.path.realpath(__file__))

olddebian = ["stretch", "jessie", "wheezy", "squeeze", "lenny"]
debianstable = "buster"

currentpath = os.getcwd()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if re.match('^-(h|-help)$', sys.argv[1]):
            usage()
            exit(0)
        else:
            print(f"{error} Bad argument")
            usage()
            exit(1)

    prerequisites()

    myhostname, mydomain = myh.set_hostname()
    myiface, myoldip, myip, renewip = myh.set_ipaddr()

    mysubnet = ".".join(ipaddr.split(".")[:-1])

    mydhcpstart, mydhcpend = set_dhcp(mysubnet)
    mypxe = set_pxe(mysubnet, myip)

    print(f"\n{ci}Server settings{c0}:")
    print(f"  - {ci}Hostname{c0}:   {myhostname}")
    print(f"  - {ci}Domain{c0}:     {mydomain}")
    if renewip:
        print(f"  - {ci}IP address{c0}: {myip}")
    print(f"{ci}DHCP settings{c0}:")
    print(f"  - {ci}DHCP range{c0}: {mydhcpstart} - {mydhcpend}")
    print(f"  - {ci}PXE server{c0}: {mypxeip}")

    confconf = input("Confirm configuration [Y/n] ? ")
    if re.match('^(n|no)$', confconf):
        exit(0)

    myh.renew_hostname(myhostname, mydomain)
    if renewip:
        myh.fix_ip(myiface, myip, myoldip)

    mypkgs = ["isc-dhcp-server"]
    myh.install_server(mypkgs)

    configure_server(mydomain, mysubnet, mydhcpstart, mydhcpend, mypxe,
                     myiface)
