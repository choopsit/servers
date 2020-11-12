#!/usr/bin/env python3

import sys
import re
import os
import socket
import struct
import fcntl
import shutil
import urllib.request

__description__ = "Usefull functions for 'servers' repo"
__author__ = "Choops <choopsbd@gmail.com>"


def usage():
    myscript = f"{os.path.basename(sys.argv[0])}"
    print(f"{ci}{__description__}\nUsage{c0}:")
    print(f"  ./{myscript} [OPTION]")
    print(f"{ci}Options{c0}:")
    print(f"  -h,--help: Print this help")
    print()


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


def get_ip(ifname):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockfd = sock.fileno()
    SIOCGIFADDR = 0x8915

    ifreq = struct.pack('16sH14s', ifname.encode('utf-8'), socket.AF_INET,
                        b'\x00'*14)
    try:
        res = fcntl.ioctl(sockfd, SIOCGIFADDR, ifreq)
    except:
        return None

    ip = struct.unpack('16sH2x4s8x', res)[2]

    return socket.inet_ntoa(ip)


def get_dns():
    dnssrv = ""

    rqpkg_cmd = "apt-get install -qq dnsutils >/dev/null"
    os.system(rqpkg_cmd)

    dnsinfo = os.popen("dig").read().split("\n")
    for line in dnsinfo:
        if "SERVER: " in line:
            dnssrv = line[line.find("(")+1 : line.find(")")]

    if dnssrv == "":
        print(f"{error} No DNS server found")
        exit(1)

    return dnssrv


def get_gw():
    getgw_cmd = "ip r | grep default"
    gateway = os.popen(getgw_cmd).read().split()[2]

    return gateway


def define_newip(subnet):
    endip = input(f"IP address ? {subnet}.")

    if re.match('^[0-9]+$', endip) and int(endip) < 255:
        return f"{subnet}.{endip}"
    else:
        print(f"{error} Invalid IP address '{subnet}.{endip}'")
        exit(1)


def set_ipaddr():
    newip = True
    iface = ""
    iprequest = ""

    for line in os.popen("ip route"):
        if line.startswith("default"):
            if line.split()[-1] == "onlink":
                iface = line.split()[-2]
            else:
                iface = line.split()[-1]

    oldipaddr = get_ip(iface)
    subnet = ".".join(oldipaddr.split(".")[:-1])

    with open("/etc/network/interfaces", "r") as f:
        for line in f:
            if line.startswith(f"iface {iface}"):
                iprequest = line.split()[-1]

    if iprequest == "static":
        print(f"{warning} IP address already fixed")
        keepip = input(f"Keep current: '{oldipaddr}' [Y/n] ? ")
        if re.match('^(n|no)', keepip.lower()):
            ipaddr = define_newip(subnet)
        else:
            newip = False
            ipaddr = oldipaddr
    else:
        ipaddr = define_newip(subnet)

    return iface, oldipaddr, ipaddr, newip


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


def fix_ip(iface, ipaddr, oldipaddr):
    getgw_cmd = "ip r | grep default | awk '{print $3}'"
    gateway = os.popen(getgw_cmd).read().rstrip("\n")

    ipconfig = "/etc/network/interfaces"
    tmpipc = "/tmp/interfaces"
    with open(ipconfig, "r") as oldf, open(tmpipc, "w") as tmpf:
        for line in oldf:
            if (ipaddr != oldipaddr and oldipaddr in line) or gateway in line:
                tmpfs.write("")
            elif line.startswith(f"iface {iface} inet"):
                staticip = f"iface {iface} inet static\n"
                staticip += f"    address {ipaddr}/24\n"
                staticip += f"    gateway {gateway}\n"
                tmpf.write(staticip)
            else:
                tmpf.write(line)
    shutil.copy(tmpipc, ipconfig)

    os.system(f"ip link set {iface} down")
    os.system(f"ip addr del {oldipaddr}/24 dev {iface}")
    os.system(f"ip addr add {ipaddr}/24 dev {iface}")
    os.system(f"ip link set {iface} up")
    os.system(f"ip route add default via {gateway}")


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


def recursive_chmod(path, perm):
    for root, dirs, files in os.walk(path):
        os.chmod(root, perm)
        for mydir in dirs:
            os.chmod(os.path.join(root, mydir), perm)
        for myfile in files:
            os.chmod(os.path.join(root, myfile), perm)


def recursive_copy(src, tgt):
    for root, dirs, files in os.walk(src):
        for item in files:
            src_path = os.path.join(root, item)
            dst_path = os.path.join(tgt, src_path.replace(f"{src}/", ""))
            if os.path.exists(dst_path):
                if os.stat(src_path).st_mtime > os.stat(dst_path).st_mtime:
                    shutil.copy(src_path, dst_path)
            else:
                shutil.copy(src_path, dst_path)
        for item in dirs:
            src_path = os.path.join(root, item)
            dst_path = os.path.join(tgt, src_path.replace(f"{src}/", ""))
            if not os.path.exists(dst_path):
                os.mkdir(dst_path)


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


def valid_email(mail):
    mailregex = "^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$"
    if re.search(mailregex, mail):
        return True
    else:
        return False


c0 = "\33[0m"
ce = "\33[31m"
cok = "\33[32m"
cw = "\33[33m"
ci = "\33[36m"

error = f"{ce}E{c0}:"
done = f"{cok}OK{c0}:"
warning = f"{cw}W{c0}:"

srcfolder = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if re.match('^-(h|-help)$', sys.argv[1]):
            usage()
            exit(0)
        else:
            print(f"{error} Bad argument")
            usage()
            exit(1)
