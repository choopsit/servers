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


def is_valid_hostname(hostname):
    if len(hostname) > 255:
        return False

    if hostname[-1] == ".":
        hostname = hostname[:-1]
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)

    return all(allowed.match(x) for x in hostname.split("."))


def set_hostname():
    oldhostname = socket.getfqdn()

    newhostname = input("Hostname (or FQDN) ? ")

    if newhostname == "":
        print(f"{warning} No hostname set")
        keepold = input(f"Keep current: '{oldhostname}' [Y/n] ? ")
        if re.match('^(n|no)$', keepold.lower()):
            exit(1)
        else:
            newhostname = oldhostname

    if not is_valid_hostname(newhostname):
        print(f"{error} Invalid hostname '{newhostname}'")
        exit(1)

    hostname = newhostname.split(".")[0]
    domain = ".".join(newhostname.split(".")[1:])

    if domain == "":
        domain = input(f"Domain name ? ")
        if not is_valid_hostname(domain):
            print(f"{error} Invalid domain name '{domain}'")
            exit(1)

    return hostname, domain


def renew_hostname(hostname, domain):
    with open("/etc/hostname", "w") as f:
        f.write(hostname)

    hostconfig = "/etc/hosts"
    tmphc = "/tmp/hosts"
    with open(hostconfig, "r") as oldf, open(tmphc, "w") as tmpf:
        for line in oldf:
            if line.startswith("127.0.1.1"):
                tmpf.write(f"127.0.1.1\t{hostname}.{domain}\t{hostname}\n")
            else:
                tmpf.write(line)
    shutil.copy(tmphc, hostconfig)
    os.system(f"hostname {hostname}")


def install_server(serverpkgs):
    sourceslist = "/etc/apt/sources.list"
    tmpfile = "/tmp/sources.list"
    with open(sourceslist, "r") as oldf, open(tmpfile, "w") as tmpf:
        for line in oldf:
            okline = True
            if "cdrom" in line or line == "#\n" or line.isspace():
                okline = False

            if okline:
                lineend = ""
                if line.endswith("main\n"):
                    lineend = " contrib non-free"
                tmpf.write(f"{line.strip()}{lineend}\n")
    shutil.copy(tmpfile, sourceslist)

    pkgs = ["vim", "ssh", "git", "curl", "build-essential", "p7zip-full",
            "tree", "htop", "rsync"]

    pkgs += serverpkgs

    print(f"{ci}Packages to install{c0}:")
    print(f"{cw}{' '.join(pkgs)}{c0}")
    goforit = input("Continue [Y/n] ? ")
    if re.match('^(n|no)', goforit.lower()):
        exit(0)

    os.system("apt update")
    os.system("apt full-upgrade -yy")
    os.system(f"apt install -yy {' '.join(pkgs)}")

    residualpkgs = []
    for line in os.popen("dpkg -l | grep ^rc"):
        residualpkgs.append(line.split()[1])
    if residualpkgs != []:
        os.system(f"apt purge -yy {' '.join(residualpkgs)}")

    os.system("apt autoremove --purge -yy")
    os.system("apt autoclean 2>/dev/null")
    os.system("apt clean 2>/dev/null")


def overwrite(src, tgt):
    if os.path.isdir(src):
        if os.path.isdir(tgt):
            shutil.rmtree(tgt)
        shutil.copytree(src, tgt, symlinks=True)
    else:
        if os.path.exists(tgt):
            os.remove(tgt)
        shutil.copy(src, tgt, follow_symlinks=False)


def vimplug_install(homefolder):
    tgtfolder = f"{homefolder}/.vim/autoload"
    os.makedirs(tgtfolder)
    rawgiturl = "https://raw.githubusercontent.com/"
    plugurl = f"{rawgiturl}junegunn/vim-plug/master/plug.vim"
    urllib.request.urlretrieve(plugurl, f"{tgtfolder}/plug.vim")


def common_config():
    swapconf = "/etc/sysctl.d/99-swappiness.conf"
    swapconfok = False
    if os.path.isfile(swapconf):
        with open(swapconf, "r") as f:
            if "vm.swappiness=5" in f.read():
                swapconfok = True
    if not swapconfok:
        with open(swapconf, "w") as f:
            for newline in ["vm.swappiness=5\n", "vm.vfs_cache_pressure=50\n"]:
                f.write(newline)
    os.system(f"sysctl -p {swapconf}")
    os.system("swapoff -av")
    os.system("swapon -av")

    sshconf = "/etc/ssh/sshd_config"
    sshconfok = False
    with open(sshconf, "r") as f:
        for line in f:
            if re.match('^PermitRootLogin yes', line):
                sshconfok = True
    if not sshconfok:
        tmpfile = "/tmp/sshd_config"
        with open(sshconf, "r") as oldf, open(tmpfile, "w") as tmpf:
            for line in oldf:
                if "PermitRootLogin" in line:
                    tmpf.write("PermitRootLogin yes\n")
                else:
                    tmpf.write(line)
        shutil.copy(tmpfile, sshconf)
    os.system("systemctl restart ssh")

    for oldvimconf in ["/root/.vimrc", "/root/.viminfo"]:
        if os.path.isfile(oldvimconf):
            os.remove(oldvimconf)

    shutil.copy(f"{srcfolder}/root/bashrc", "/root/.bashrc")
    for conf in ["vim", "profile"]:
        overwrite(f"{srcfolder}/root/{conf}", f"/root/.{conf}")

    vimplug_install("/root")

    os.system("vim +PlugInstall +qall && clear")


def add_saltstack_repo():
    os.system("apt install -yy gnupg2")

    repokey = "/tmp/salt.pub"
    salturl = f"repo.saltstack.com/py3/debian/{debianstablev}/amd64/latest"
    keyurl = f"https://{salturl}/SALTSTACK-GPG-KEY.pub"

    urllib.request.urlretrieve(keyurl, repokey)
    os.system(f"apt-key add {repokey}")

    with open("/etc/apt/sources.list.d/saltstack.list", "w") as f:
        f.write("# SaltStack")
        f.write(f"deb http://{salturl} {debianstable} main")

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
        renew_hostname(myhostname,·mydomain)

    add_saltstack_repo()
    mypkgs = ["salt-minion"]
    install_server(mypkgs)

    configure_server()
