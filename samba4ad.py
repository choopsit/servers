#!/usr/bin/env python3

import sys
import re
import os
import socket
import struct
import fcntl
import shutil
import urllib.request
import tarfile
import zipfile
import _myhelpers as myh

__description__ = "Install an Active Directory Domain Controller on Debian"
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


def set_admin_password():
    pwdnotice = "Set Administrator's password for Samba4 Active Directory "
    pwdnotice += "(at least 8 characters including at least one uppercase "
    pwdnotice += "letter and one number): "
    password = input(pwdnotice)

    if (any(x.isupper() for x in password) and
        any(x.islower() for x in password) and
        any(x.isdigit() for x in password) and len(password) >= 8):
        return password
    else:
        print(f"{error} Password is too weak")
        exit(1)


def set_password_policy():
    policy = {"weak": False, "infinite": False}

    weakpwd = input("Allow weak passwords [y/N] ? ")
    if re.match('^(y|yes)', weakpwd.lower()):
        policy["weak"] = True

    infinitepwd = input("Unlimit passwords age [y/N] ? ")
    if re.match('^(y|yes)', infinitepwd.lower()):
        policy["infinite"] = True

    return policy


def configure_server(hostname, domain, ipaddr, gateway):
    print(f"{ci}Configuring Samba4 AD server...{c0}")
    myh.common_config()

    with open("/etc/hostname", "w") as f:
        f.write(f"{hostname}.{domain}")
    os.system(f"hostname {hostname}.{domain}")

    print(f"{ci}Configuring Bind...{c0}")

    bindconf = "/etc/default/bind9"
    shutil.copy(bindconf, f"{bindconf}.o")
    with open(f"{bindconf}.o", "r") as oldf, open(bindconf, "w")as newf:
        for line in oldf:
            if line.satrtswith("\"OPTIONS=\"-u bind"):
                newf.write("\"OPTIONS=\"-u bind -4\n")
            else:
                newf.write(line)

    bindopt = "/etc/bind/named.conf.options"
    shutil.copy(bindopt, f"{bindopt}.o")
    bindoptsrc = f"{srcfolder}/conf/bind/named.conf.options"
    subnet = ".".join(ipaddr.split(".")[0:3])
    with open(bindoptsrc, "r") as oldf, open(bindopt, "w")as newf:
        for line in oldf:
            if line.startswith("acl internals"):
                newf.write("acl internals { 127.0.0.0/8; "+subnet+".0/24; };")
            else:
                newf.write(line)

    bindloc = "/etc/bind/named.conf.local"
    addloc = False
    with open(bindloc, "r") as f:
        if "AD DNS Zone" not in f.read():
            addloc = True
    if addloc:
        shutil.copy(bindloc, f"{bindloc}.o")
        bindlib = "/usr/lib/x86_64-linux-gnu/samba/bind9/dlz_bind9_11.so"
        with open(bindloc, "a") as f:
            f.write("dlz \"AD DNS Zone\" {\n")
            f.write("    # For BIND 9.11\n")
            f.write(f"    database \"dlopen {bindlib}\";\n")
            f.write("};\n")

    print(f"{ci}Configuring Samba...{c0}")
    # TODO: Samba4 configuration and Active Directory provising

    with open("/etc/resolv.conf", "w") as f:
        f.write(f"domain {domain}\n")
        f.write(f"search {domain}\n")
        f.write(f"nameserver {ipaddr}\n")


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

    getgw_cmd = "ip r | grep default | awk '{print $3}'"
    mygateway = os.popen(getgw_cmd).read().rstrip("\n")

    mypass = set_admin_password()
    mypasspolicy = set_password_policy()

    print(f"\n{ci}Server settings{c0}:")
    print(f"  - {ci}Hostname{c0}:   {myhostname}")
    print(f"  - {ci}Domain{c0}:     {mydomain}")
    if renewip:
        print(f"  - {ci}IP address{c0}: {myip}")
    print(f"{ci}service settings{c0}:")

    confconf = input("Confirm configuration [Y/n] ? ")
    if re.match('^(n|no)$', confconf):
        exit(0)

    myh.renew_hostname(myhostname, mydomain)
    if renewip:
        myh.fix_ip(myiface, myip, myoldip)

    mypkgs = ["bind9", "ntp", "acl", "samba", "krb5-config", "krb5-user",
              "winbind", "libnss-winbind", "libpam-winbind", "smbclient",
              "net-tools", "dnsutils"]
    os.system("export DEBIAN_FRONTEND=noninteractive")
    myh.install_server(mypkgs)

    configure_server(myhostname, mydomain, myip, mygateway, mypass,
                     mypasspolicy)
