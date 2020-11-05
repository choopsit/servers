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

__description__ = "Install a local Debian and/or Ubuntu repo on Debian"
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


def set_repo():
    defaultname = "repo"
    reponame = input(f"Repository name [default: '{defaultname}'] ? ")
    if reponame == "":
        reponame = defaultname
    elif len(reponame) == 2:
        if not re.match('^[a-z0-9]+$', reponame):
            print(f"{error} Invalid repository name '{reponame}'")
            exit(1)
    elif not re.match('^[a-z0-9]+[a-z0-9_-]+[a-z0-9]$', reponame):
        print(f"{error} Invalid repository name '{reponame}'")
        exit(1)

    repofolder = f"/var/www/html/{reponame}"

    maintainer = input("Maintainer's name ? ")
    if maintainer == "":
        print(f"{error} Maintainer's name can not be empty")
        exit(1)

    maintainermail = input("Mantainer's email address ? ")
    if maintainermail == "":
        print(f"{error} Maintainer's email address can not be empty")
        exit(1)
    elif not myh.valid_email(maintainermail):
        print(f"{error} Invalid email address '{maintainermail}'")

    gpgpass = input("GPG passphrase ? ")
    if maintainer == "":
        print(f"{error} GPG passphrase can not be empty")
        exit(1)

    return reponame, repofolder, maintainer, maintainermail, gpgpass


def select_distros():
    distlist = []

    okdists = ["debian", "ubuntu"]
    ubuntults = "focal"
    ubuntucurrent = "groovy"
    for dist in okdists:
        if dist == "debian":
            okvers = [f"{debianstable} (stable)", f"{debiantesting} (testing)",
                      "sid"]
        else:
            okvers = [f"{ubuntults} (LTS)", f"{ubuntucurrent} (current)"]

        print(f"{ci}Available versions of {dist.capitalize()}{c0}:")
        for i in range(len(okvers)):
            print(f"  {i}) {ci}{okvers[i]}{c0}")
        vchoicenotice = "[separated by spaces, 'a' for all, <Enter> for none]"
        vchoice = input(f"Versions to supply {vchoicenotice} ? ")

        chosenversions = []
        if re.match('^(a|all)$', vchoice):
            for i in range(len(okvers)):
                chosenversions.append(okvers[i].split()[0])
        else:
            vchoices = vchoice.split()
            for choice in vchoices:
                try:
                    ichoice = int(choice)
                except ValueError:
                    print(f"{error} Out of range choice '{choice}'")
                    exit(1)
                if ichoice in range(len(okvers)):
                    chosenversions.append(okvers[ichoice].split()[0])
                else:
                    print(f"{error} Invalid choice '{ichoice}'")
                    exit(1)

        for version in chosenversions:
            distlist.append(f"{dist} {version}")

    return distlist


def generate_gpgkey(maintainer, maintainermail, gpgpass):
    tmpfolder = "/tmp"

    keyfolder = "/root/.gnupg"
    if os.path.isdir(keyfolder):
        shutil.move(keyfolder, "/root/old.gnupg")

    with open(f"{tmpfolder}/key_ref", "w") as f:
        f.write("%echo Generating a basic OpenPGP key\n")
        f.write("Key-Type: RSA\n")
        f.write("Key-Length: 4096\n")
        f.write(f"Name-Real: {maintainer}\n")
        f.write(f"Name-Email: {maintainermail}\n")
        f.write("Expire-Date: 0\n")
        f.write(f"Passphrase: {gpgpass}\n")
        f.write("%commit\n")
        f.write("%echo done\n")

    with open(f"{tmpfolder}/entropy.sh", "w") as f:
        f.write("#!/usr/bin/env bash\n\n")
        f.write("while true; do\n")
        f.write("  cp -rp /etc/ /tmp/\n")
        f.write("  rm -rf /tmp/etc/\n")
        f.write("done\n")
    os.chmod(f"{tmpfolder}/entropy.sh", 0o755)

    os.system(f"gpg --batch --gen-key {tmpfolder}/key_ref")
    # TODO: run f"{tmpfolder}/entropy.sh" in parallel and stop it when done

    keyid_cmd = "gpg --list-keys | grep -P '^\ ' | grep -o '.\{8\}$'"
    keyid = os.popen(keyid_cmd).read()

    return keyid


def add_repobranches(repofolder, distlist, keyid):
    repo = repofolder.split("/")[-1]
    for dist in distlist:
        distro = dist.split()[0]
        codename = dist.split()[1]
        repodist = f"{repofolder}/conf/distributions"
        with open(repodist, "a") as f:
            f.write(f"Origin: {repo}\n")
            f.write(f"Label: {repo}\n")
            f.write(f"Codename: {codename}\n")
            f.write("Architectures: i386 amd64 source\n")
            f.write("Components: main\n")
            f.write(f"Description: Local repository for {dist}\n")
            f.write(f"SignWith: {keyid}\n")


def configure_server(repofolder, maintainer, maintainermail, gpgpass,
                     distlist):
    print(f"{ci}Configuring local repository server...{c0}")
    myh.common_config()

    if not os.path.isdir(repofolder):
        os.makedirs(repofolder)

    os.system("systemctl restart apache2")

    for subfolder in ["conf", "incoming", "key"]:
        os.makedirs(f"{repofolder}/{subfolder}")

    repodist = f"{repofolder}/conf/distributions"
    if os.path.isfile(repodist):
        os.remove(repodist)
    with open(repodist, "w") as f:
        f.write("")

    repokeyid = generate_gpgkey(maintainer, maintainermail, gpgpass)

    add_repobranches(repofolder, distlist, repokeyid)


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
debiantesting = "bullseye"

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

    myrepo, myfolder, mymaintainer, mymaintainermail, mygpgpass = set_repo()
    mydistlist = select_distros()

    print(f"\n{ci}Server settings{c0}:")
    print(f"  - {ci}Hostname{c0}:   {myhostname}")
    print(f"  - {ci}Domain{c0}:     {mydomain}")
    if renewip:
        print(f"  - {ci}IP address{c0}: {myip}")
    print(f"{ci}Local repository settings{c0}:")
    print(f"  - {ci}Repo folder{c0}: {myfolder}")
    print(f"  - {ci}Maintainer{c0}:")
    print(f"    - {ci}Name{c0}:  {mymaintainer}")
    print(f"    - {ci}Email{c0}: {mymaintainermail}")
    print(f"  - {ci}GPG passphrase{c0}: {mygpgpass}")
    print(f"  - {ci}Distributions to supply{c0}: {mydistlist}")

    confconf = input("Confirm configuration [Y/n] ? ")
    if re.match('^(n|no)$', confconf):
        exit(0)

    myh.renew_hostname(myhostname, mydomain)
    if renewip:
        myh.fix_ip(myiface, myip, myoldip)

    mypkgs = ["apache2", "reprepro"]
    myh.install_server(mypkgs)

    configure_server(myfolder, mymaintainer, mymaintainermail, mygpgpass,
                     mydistlist)
