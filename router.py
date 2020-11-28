#!/usr/bin/env python3

import sys
import re
import os
import _myhelpers_ as myh

__description__ = "Make a Debian install with 2 network interfaces work as a "
__description__ += "router"
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


def get_laniface(waniface):
    laniface = ""
    ifacelist = []

    for line in os.popen("ip l"):
        for i in range(2, 4):
            if line.startswith(f"{i}:"):
                ifacelist.append(line.split(": ")[1])

    for iface in ifacelist:
        if iface != waniface:
            laniface = iface

    if laniface == "":
        print(f"{error} Unable to find LAN interface")
        exit(1)

    return laniface


def set_laniface(laniface, lanip):
    lanconf = "/etc/network/interfaces.d/mylan"
    with open(lanconf, "w") as f:
        f.write("# LAN interface\n")
        f.write(f"auto {laniface}"+"\n")
        f.write(f"iface {laniface} inet static"+"\n")
        f.write(f"    address {lanip}/24"+"\n")

    for state in ["down", "up"]:
        os.system(f'ip link set "{laniface}" {state}')


def establish_routing(waniface):
    routingconf = "/etc/sysctl.conf"
    tmpfile = "/tmp/sysctl.conf"
    myh.overwrite(routingconf, tmpfile)
    with open(tmpfile, "r") as oldf, open(routingconf, "w") as newf:
        for line in oldf:
            if line == "#net.ipv4.ip_forward=1\n":
                newf.write("net.ipv4.ip_forward=1\n")
            else:
                newf.write(line)

    cmds = ["sysctl -p", "sysctl --system",
            f"iptables -t nat -A POSTROUTING -o '{waniface}' -j MASQUERADE",
            "iptables -A FORWARD -j ACCEPT",
            "iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT",
            "apt install -y iptables-persistent"]

    for cmd in cmds:
        os.system(cmd)


def configure_dnsmasq(laniface, lanip):
    dnsmconf = "/etc/dnsmasq.conf"
    myh.overwrite(dnsmconf, f"{dnsmconf}.o")

    subnet = ".".join(lanip.split(".")[:-1])
    with open(dnsmconf, "w") as f:
        f.write(f"interface={laniface}"+"\n")
        f.write("listen-address=127.0.0.1\n")
        f.write(f"dhcp-range={subnet}.1,{subnet}.254,12h"+"\n")


def configure_server(waniface, laniface, lanip):
    print(f"{ci}Configuring router...{c0}")
    myh.common_config()

    set_laniface(laniface, lanip)
    establish_routing(waniface)
    configure_dnsmasq(laniface, lanip)

    print(f"{done} 'router' installed")
    rebootnow = myh.yesno("Reboot now", "y")
    if not re.match('^(n|no)$', rebootnow):
        os.system("reboot")


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

    mywaniface = myh.get_iface()
    mywanip = myh.get_ip(mywaniface)
    mygateway = myh.get_gw()
    mydns = myh.get_dns()

    print(f"{ci}LAN settings{c0}:")
    mylaniface = get_laniface(mywaniface)
    myoldlanip, mylanip, renewip = myh.set_ipaddr(mylaniface)

    print(f"\n{ci}Server settings{c0}:")
    print(f"  - {ci}Hostname{c0}:       {myhostname}")
    print(f"  - {ci}Domain{c0}:         {mydomain}")
    print(f"  - {ci}WAN interface{c0}:  {mywaniface}")
    print(f"  - {ci}WAN IP address{c0}: {mywanip}")
    print(f"  - {ci}Gateway{c0}:        {mygateway}")
    print(f"  - {ci}Nameserver{c0}:     {mydns}")
    print(f"{ci}Router settings{c0}:")
    print(f"  - {ci}LAN interface{c0}:  {mylaniface}")
    print(f"  - {ci}LAN IP address{c0}: {mylanip}")

    confconf = input("Confirm configuration [Y/n] ? ")
    if re.match('^(n|no)$', confconf):
        exit(0)

    myh.renew_hostname(myhostname, mydomain)

    mypkgs = ["dnsmasq"]
    myh.install_server(mypkgs)

    configure_server(mywaniface, mylaniface, mylanip)
