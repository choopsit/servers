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
import _myhelpers_ as myh

__description__ = "Install SaltStack minion on Debian"
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


def add_saltstack_repo():
    os.system("apt-get install -qq gnupg2")

    repokey = "/tmp/salt.pub"
    salturl = f"repo.saltstack.com/py3/debian/{debianstablev}/amd64/latest"
    keyurl = f"https://{salturl}/SALTSTACK-GPG-KEY.pub"

    urllib.request.urlretrieve(keyurl, repokey)
    os.system(f"apt-key add {repokey}")

    with open("/etc/apt/sources.list.d/saltstack.list", "w") as f:
        f.write("# SaltStack\n")
        f.write(f"deb http://{salturl} {debianstable} main\n")

    os.system("apt update")


def configure_server():
    print(f"{ci}Configuring server...{c0}")
    common_config()


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
debianstablev = "10"

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

    newhostname = input("Renew hostname [y/N] ? ")
    if re.match('^(y|yes)', newhostname.lower()):
        myhostname, mydomain = set_hostname()
        print(f"\n{ci}Server settings{c0}:")
        print(f"  - {ci}Hostname{c0}:   {myhostname}")
        print(f"  - {ci}Domain{c0}:     {mydomain}")

        confconf = input("Confirm configuration [Y/n] ? ")
    else:
        confconf = input("Install 'salt-minion' [Y/n] ? ")
    if re.match('^(n|no)$', confconf):
        exit(0)

    if re.match('^(y|yes)', newhostname.lower()):
        myh.renew_hostname(myhostname, mydomain)

    add_saltstack_repo()
    mypkgs = ["salt-minion"]
    myh.install_server(mypkgs)

    configure_server()
