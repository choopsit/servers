#!/usr/bin/env python3

import sys
import re
import os
import shutil
import urllib.request
import tarfile
import zipfile
import _myhelpers_ as myh

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


def choose_me(choicesref):
    chosenones = []

    hchoice = "'1 0' for multiple choice, 'a' for all, press <Enter> for none"
    nchoice = input(f"Your choice [{hchoice}]: ")

    if re.match('^(a|all)$', nchoice):
        chosenones = choicesref
    else:
        nchoicelist = nchoice.split()
        for choice in nchoicelist:
            try:
                intchoice = int(choice)
                chosenones.append(choicesref[intchoice])
            except ValueError:
                print(f"{error} Invalid choice '{choice}'")
                chosenones = choose_me(choicesref)
            if intchoice not in range(choicesref):
                print(f"{error} Out of range choice '{choice}'")
                chosenones = choose_me(choicesref)

    return chosenones


def choose_utils(utilsref, dictutilsref):
    chosenutils = []

    print(f"{ci}Available utilities{c0}:")
    i = 0
    for key, _ in dictutilsref.items():
        print(f"  {i}) {ci}{key}{c0}")
        i += 1

    chosenutils = choose_me(utilsref)

    dictutils = {}
    for chosen in chosenutils:
        dictutils[chosen] = dictutilsref[chosen]

    return dictutils


def choose_netboots(netbootsref, dictnetbootsref):
    print(f"{ci}Available installers{c0}:")
    i = 0
    for key, _ in dictnetbootsref.items():
        print(f"  {i}) {ci}{key}{c0}")
        i += 1

    chosennetboots = choose_me(netbootsref)

    dictnetboots = {}
    for chosen in chosennetboots:
        dictnetboots[chosen] = dictnetbootsref[chosen]

    return dictnetboots


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
    myh.common_config()

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
    myh.recursive_chmod(tftproot, 0o755)

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
                f"{tftproot}/{pxebg}")

    defaultf = f"{tftproot}/pxelinux.cfg/default"
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

    scriptfolder = f"{srcfolder}/conf/pxe/bin"
    for script in os.listdir(scriptfolder):
        target = f"/usr/local/bin/{script}"
        if os.path.exists(target):
            os.remove(target)
        shutil.copy(f"{scriptfolder}/{script}", target)

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

    myhostname, mydomain = myh.set_hostname()
    myiface, myoldip, myip, renewip = myh.set_ipaddr()

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

    myh.renew_hostname(myhostname, mydomain)
    if renewip:
        myh.fix_ip(myiface, myip, myoldip)

    mypkgs = ["tftpd-hpa", "syslinux-utils", "syslinux", "pxelinux",
              "nfs-kernel-server"]
    myh.install_server(mypkgs)

    configure_server(myiface, myip, mydomain, mytitle, myutils, mynetboots)
