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

__description__ = "Install Debian PXE Boot server"
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


def set_pxetitle(domain):
    pxetitle = input(f"PXE title [default '{domain} PXE Boot'] ? ")
    if pxetitle == "":
        pxetitle = f"{domain} PXE Boot"

    return pxetitle


def ref_utils(ipaddr):
    ufiles = []
    uurls = []
    umenus = []

    ufiles.append("clonezilla.iso")
    # czurl = "https://osdn.net/dl/clonezilla/"
    # czurl += f"clonezilla-live-{clonezillalatest}-amd64.iso"
    czurl = "https://sourceforge.net/projects/clonezilla/files/"
    czurl += f"clonezilla_live_stable/{clonezillalatest}/"
    czurl += f"clonezilla-live-{clonezillalatest}-amd64.iso"
    uurls.append(czurl)
    czmenu = "\nLABEL Clonezilla\n"
    czmenu += "  KERNEL clonezilla/live/vmlinuz\n"
    czmenu += "  APPEND rootfstype=nfs netboot=nfs"
    czmenu += f" nfsroot={ipaddr}:{tftproot}/clonezilla"
    czmenu += " initrd=clonezilla/live/initrd.img boot=live union=overlay"
    czmenu += " username=user config components quiet noswap"
    czmenu += " edd=on nomodeset nodmraid locales= keyboard-layouts="
    czmenu += " ocs_live_run=\"ocs-live-general\" ocs_live_extra_param=\"\""
    czmenu += " ocs_live_batch=no ip= vga=788 net.ifnames=0 nosplash"
    czmenu += " i915.blacklist=yes radeonhd.blacklist=yes"
    czmenu += " nouveau.blacklist=yes vmwgfw.enable_fbdev=1\n"
    umenus.append(czmenu)

    ufiles.append("gparted.zip")
    gpurl = "https://sourceforge.net/projects/gparted/files/"
    gpurl += f"gparted-live-stable/{gpartedlatest}/"
    gpurl += f"gparted-live-{gpartedlatest}-amd64.zip"
    uurls.append(gpurl)
    gpmenu = "\nLABEL Gparted\n"
    gpmenu += "  KERNEL gparted/vmlinuz\n"
    gpmenu += "  APPEND initrd=gparted/initrd.img boot=live"
    gpmenu += " config union=overlay username=user noswap noprompt vga=788"
    gpmenu += f" fetch=tftp://{ipaddr}/gparted/filesystem.squashfs\n"
    umenus.append(gpmenu)

    ufiles.append("memtest.zip")
    mturl = f"http://www.memtest.org/download/{memtestlatest}/"
    mturl += f"memtest86+-{memtestlatest}.bin.zip"
    uurls.append(mturl)
    mtmenu = "\nLABEL Memtest86+\n  KERNEL memtest\n"
    umenus.append(mtmenu)

    dictutilsref = {}
    for i in range(len(utilities)):
        dictutilsref[utilities[i]] = [ufiles[i], uurls[i], umenus[i]]

    return dictutilsref


def choose_utils(utilsref, dictutilsref):
    print(f"{ci}Available utilities{c0}:")
    i = 0
    for key, _ in dictutilsref.items():
        print(f"  {i}) {ci}{key}{c0}")
        i += 1
    hchoice = "'1 0' for multiple choice, 'a' for all, press <Enter> for none"
    uchoice = input(f"Your choice [{hchoice}]: ")

    chosenutils = []
    if re.match('^(a|all)$', uchoice):
        chosenutils = utilities
    else:
        uchoicelist = uchoice.split()
        for choice in uchoicelist:
            try:
                intchoice = int(choice)
                chosenutils.append(utilsref[intchoice])
            except ValueError:
                print(f"{error} Invalid choice '{choice}'")
                exit(1)

    dictutils = {}
    for chosen in chosenutils:
        dictutils[chosen] = dictutilsref[chosen]

    return dictutils


def ref_netboots():
    nfiles = []
    nurls = []
    nmenus = []

    for nb in netboots:
        nfiles.append(f"{nb.split()[0]}_netboot.tar.gz")

    deburl = "http://ftp.nl.debian.org/debian/dists/stable/main/"
    deburl += "installer-amd64/current/images/netboot/netboot.tar.gz"
    nurls.append(deburl)
    debmenu = "\nLABEL Debian stable\n"
    debmenu += "  KERNEL debianstable/debian-installer/amd64/linux\n"
    debmenu += "  APPEND initrd=debianstable/debian-installer/amd64/initrd.gz"
    debmenu += " vga=788"
    debmenu += " ramdisk_size=9372 root=/dev/rd/0 devfs=mount,dall rw --\n"
    nmenus.append(debmenu)

    uburl = f"http://archive.ubuntu.com/ubuntu/dists/{ubuntults}-updates/main/"
    uburl += "installer-amd64/current/legacy-images/netboot/netboot.tar.gz"
    nurls.append(uburl)
    ubmenu = "\nLABEL Ubuntu LTS\n"
    ubmenu += "  KERNEL ubuntults/ubuntu-installer/amd64/linux\n"
    ubmenu += "  APPEND initrd=ubuntults/ubuntu-installer/amd64/initrd.gz"
    ubmenu += " vga=788"
    ubmenu += " locale=fr_FR.UTF-8;keyboard-configuration/layoutcode=fr\n"
    nmenus.append(ubmenu)

    dictnetbootsref = {}
    for i in range(len(netboots)):
        dictnetbootsref[netboots[i]] = [nfiles[i], nurls[i], nmenus[i]]

    return dictnetbootsref


def choose_netboots(netbootsref, dictnetbootsref):
    print(f"{ci}Available installers{c0}:")
    i = 0
    for key, _ in dictnetbootsref.items():
        print(f"  {i}) {ci}{key}{c0}")
        i += 1
    hchoice = "'1 0' for multiple choice, 'a' for all, press <Enter> for none"
    nchoice = input(f"Your choice [{hchoice}]: ")

    chosennetboots = []
    if re.match('^(a|all)$', nchoice):
        chosennetboots = netboots
    else:
        nchoicelist = nchoice.split()
        for choice in nchoicelist:
            try:
                intchoice = int(choice)
                chosennetboots.append(netbootsref[intchoice])
            except ValueError:
                print(f"{error} Invalid choice '{choice}'")
                exit(1)

    dictnetboots = {}
    for chosen in chosennetboots:
        dictnetboots[chosen] = dictnetbootsref[chosen]

    return dictnetboots


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


def recursive_chmod(path):
    for root, dirs, files in os.walk(path):
        os.chmod(root, 0o755)
        for mydir in dirs:
            os.chmod(os.path.join(root, mydir), 0o755)
        for myfile in files:
            os.chmod(os.path.join(root, myfile), 0o755)


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


def add_menu_to_default(menutitle, defaultf):
    with open(defaultf, "a") as f:
        f.write(f"\nLABEL {menutitle.capitalize()}\n")
        f.write("KERNEL vesamenu.c32\n")
        f.write(f"APPEND pxelinux.cfg/{menutitle.lower()}\n")


def download_netboot(distro, dlfile, url):
    print(f"  - {ci}Downloading {distro}...{c0}")
    urllib.request.urlretrieve(url, f"/tmp/{dlfile}")

    print(f"  - {ci}Adding {distro} to {tftproot}...{c0}")
    nbpath = f"{tftproot}/{distro.lower().replace(' ', '')}"
    if os.path.isdir(nbpath):
        shutil.deltree(nbpath)
    os.makedirs(nbpath)

    os.chdir(nbpath)
    tar = tarfile.open(f"/tmp/{dlfile}", "r:gz")
    tar.extractall()
    tar.close()
    os.chdir(currentpath)


def deploy_netboots(netboots, menufile):
    for key, val in netboots.items():
        download_netboot(key, val[0], val[1])
        with open(menufile, "a") as f:
            f.write(val[2])


def download_util(util, dlfile, url):
    print(f"  - {ci}Downloading {util}...{c0}")
    urllib.request.urlretrieve(url, f"/tmp/{dlfile}")

    print(f"  - {ci}Adding {util} to {tftproot}...{c0}")
    if util == "clonezilla":
        upath = f"{tftproot}/clonezilla"
        partimagfolder = "/home/partimag"

        if not os.path.exists(partimagfolder):
            os.makedirs(partimagfolder)
        os.chmod(partimagfolder, 0o777)

        mnt_cmd = f"mount -o loop -t iso9660 /tmp/{dlfile} /mnt"
        if os.system(mnt_cmd) == 0:
            if os.path.isdir(upath):
                shutil.deltree(upath)
            shutil.copytree("/mnt", upath, symlinks=True)
            umnt_cmd = "umount /mnt"
            os.system(umnt_cmd)
        else:
            print(f"{error} Failed to mount {dlfile} on /mnt")

        nfsopt = "rw,async,no_wdelay,root_squash,insecure_locks,"
        nfsopt += "no_subtree_check"
        nfsconf = "/etc/exports"
        nfsshares = [f"{tftproot}/clonezilla", f"{partimagfolder}"]
        for share in nfsshares:
            with open(nfsconf, "a+") as f:
                if share not in f.read():
                    f.write(f"{share} *({nfsopt})\n")
        os.system("systemctl restart nfs-kernel-server")

    elif util == "gparted":
        upath = f"{tftproot}/gparted"
        tmppath = "/tmp/gparted"

        if os.path.isdir(tmppath):
            shutil.deltree(tmppath)
        os.makedirs(tmppath)

        with zipfile.ZipFile(f"/tmp/{dlfile}", "r") as zipref:
            zipref.extractall(tmppath)

        if os.path.isdir(upath):
            shutil.deltree(upath)
        os.makedirs(upath)
        for gpfile in ["initrd.img", "vmlinuz", "filesystem.squashfs"]:
            shutil.copy(f"{tmppath}/live/{gpfile}", f"{upath}/{gpfile}")

    elif util == "memtest86+":
        upath = f"{tftproot}/memtest"

        with zipfile.ZipFile(f"/tmp/{dlfile}", "r") as zipref:
            zipref.extractall("/tmp")

        shutil.copy(f"/tmp/memtest86+-{memtestlatest}.bin", upath)
        os.chmod(upath, 0o755)


def deploy_utils(utils, menufile):
    for key, val in utils.items():
        download_util(key, val[0], val[1])
        with open(menufile, "a") as f:
            f.write(val[2])


def generate_menu(menutitle, pxebg, pxetitle, netboots, utils):
    print(f"{ci}Generating '{menutitle.capitalize()}' menu...{c0}")
    menufile = f"{tftproot}/pxelinux.cfg/{menutitle}"
    if not os.path.isfile(menufile):
        with open(menufile, "w") as f:
            f.write(f"MENU BACKGROUND {pxebg}\n")
            f.write("MENU COLOR border * #80a9a9a9 #24242400 std\n")
            f.write("MENU COLOR title  * #80b0c4de #00000000 std\n")
            f.write("MENU COLOR sel    * #4080ffff #24242400 std\n")
            f.write("MENU COLOR tabmsg * #40f8f8ff #24242424 std\n")
            f.write(f"MENU TITLE {pxetitle} - {menutitle.capitalize()}\n\n")
            f.write("LABEL Back to Principal Menu\n")
            f.write("  KERNEL vesamenu.c32\n")
            f.write("  APPEND pxelinux.cfg/default\n")
            f.write("  MENU DEFAULT\n\n")
            f.write("MENU SEPARATOR\n")

    if menutitle == "install":
        deploy_netboots(netboots, menufile)
    elif menutitle == "utilities":
        deploy_utils(utils, menufile)


def configure_server(iface, ipaddr, domain, pxetitle, utils, netboots):
    print(f"{ci}Configuring PXE server...{c0}")
    common_config()

    if not os.path.isdir(tftproot):
        os.makedirs(tftproot)

    tftpconf = "/etc/default/tftpd-hpa"
    with open(tftpconf, "w") as f:
        f.write(f"TFTP_USERNAME=\"tftp\"\n")
        f.write(f"TFTP_DIRECTORY=\"{tftproot}\"\n")
        f.write(f"TFTP_ADDRESS=\"{ipaddr}:69\"\n")
        f.write(f"TFTP_OPTIONS=\"--secure\"\n")

    for srvcop in ["enable", "restart"]:
        os.system(f"systemctl {srvcop} tftpd-hpa")

    for biosfile in ["chain.c32", "mboot.c32", "menu.c32", "reboot.c32",
                     "vesamenu.c32", "libcom32.c32", "libutil.c32",
                     "ldlinux.c32", "poweroff.c32"]:
        biossrc = "/usr/lib/syslinux/modules/bios"
        shutil.copy(f"{biossrc}/{biosfile}", f"{tftproot}/{biosfile}")

    shutil.copy("/usr/lib/PXELINUX/pxelinux.0", f"{tftproot}/pxelinux.0")
    recursive_chmod(tftproot)

    pxeconf = "/etc/pxe.conf"
    with open(pxeconf, "w") as f:
        f.write("# which interface to use:\n")
        f.write(f"interface={iface}\n")
        f.write(f"default_address={ipaddr}\n\n")
        f.write("# tftpd base dir:\n")
        f.write(f"tftpdbase={tftproot}\n\n")
        f.write("# domain name:\n")
        f.write(f"domain={domain}\n")

    if not os.path.isdir(f"{tftproot}/pxelinux.cfg"):
        os.makedirs(f"{tftproot}/pxelinux.cfg")

    pxebg = f"debian_bg.png"
    shutil.copy(f"{srcfolder}/conf/pxe/{pxebg}",
                f"{tftproot}/pxelinux.cfg/{pxebg}")

    defaultf = f"{tftproot}/pxelinux.cfg/default"
    # defaultref = f"{srcfolder}/conf/pxe/menu_default"
    # with open(defaultref, "r") as ref, open(defaultf, "w") as newf:
    #     for line in ref:
    #         if line.startswith("MENU BACKGROUND"):
    #             newf.write(f"MENU BACKGROUND {pxebg}\n")
    #         elif line.startswith("MENU TITLE"):
    #             newf.write(f"MENU TITLE {pxetitle}\n")
    #         else:
    #             newf.write(line)
    
    with open(defaultf, "w") as f:
        f.write("# Visual interface:\n")
        f.write("UI vesamenu.c32\n")
        f.write("MENU RESOLUTION 1024 768\n")
        f.write(f"MENU BACKGROUND {pxebg}\n")
        f.write("MENU COLOR border * #80a9a9a9 #24242400 std\n")
        f.write("MENU COLOR title  * #80b0c4de #00000000 std\n")
        f.write("MENU COLOR sel    * #4080ffff #24242400 std\n")
        f.write("MENU COLOR tabmsg * #40f8f8ff #24242424 std\n")
        f.write(f"MENU TITLE {pxetitle}\n")
        f.write("prompt 0\n")
        f.write("kbdmap french.kbd\n")
        f.write("timeout 100\n\n")
        f.write("LABEL Boot from 1st hard drive\n")
        f.write("  COM32 chain.c32\n")
        f.write("  APPEND hd0 0\n")
        f.write("  MENU DEFAULT\n\n")
        f.write("LABEL Shutdown\n")
        f.write("  KERNEL poweroff.c32\n\n")
        f.write("LABEL Reboot\n")
        f.write("  KERNEL reboot.c32\n\n")
        f.write("MENU SEPARATOR\n")

    menutitles = []
    if netboots != {}:
        menutitles.append("install")

    if utils != {}:
        menutitles.append("utilities")

    for menutitle in menutitles:
        generate_menu(menutitle, pxebg, pxetitle, netboots, utils)
        with open(defaultf, "r") as f:
            if f"pxelinux.cfg/{menutitle}" not in f.read():
                add_menu_to_default(menutitle, defaultf)

    print(f"{done} PXE server ready to use")


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

clonezillalatest = "2.6.7-28"  # Check https://clonezilla.org/downloads.php
gpartedlatest = "1.1.0-5"      # Check https://gparted.org/download.php
memtestlatest = "5.31b"        # Check http://www.memtest.org
utilities = ["clonezilla", "gparted", "memtest86+"]

ubuntults = "focal"
netboots = ["debian stable", "ubuntu LTS"]

tftproot = "/srv/tftp"

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

    myhostname, mydomain = set_hostname()
    myiface, myoldip, myip, renewip = set_ipaddr()
    mytitle = set_pxetitle(mydomain)

    refutilsdict = ref_utils(myip)
    myutils = choose_utils(utilities, refutilsdict)
    refnetbootsdict = ref_netboots()
    mynetboots = choose_netboots(netboots, refnetbootsdict)

    print(f"\n{ci}Server settings{c0}:")
    print(f"  - {ci}Hostname{c0}:   {myhostname}")
    print(f"  - {ci}Domain{c0}:     {mydomain}")
    if renewip:
        print(f"  - {ci}IP address{c0}: {myip}")
    print(f"{ci}PXE settings{c0}:")
    print(f"  - {ci}Title{c0}:      {mytitle}")

    if myutils != {}:
        print(f"  - {ci}Utilities{c0}:")
        for key, _ in myutils.items():
            print(f"    - {key}")

    if mynetboots != {}:
        print(f"  - {ci}Installers{c0}:")
        for key, _ in mynetboots.items():
            print(f"    - {key}")

    confconf = input("Confirm configuration [Y/n] ? ")
    if re.match('^(n|no)$', confconf):
        exit(0)

    renew_hostname(myhostname, mydomain)
    if renewip:
        fix_ip(myiface, myip, myoldip)

    mypkgs = ["tftpd-hpa", "syslinux-utils", "syslinux", "pxelinux",
              "nfs-kernel-server"]
    install_server(mypkgs)

    configure_server(myiface, myip, mydomain, mytitle, myutils, mynetboots)
