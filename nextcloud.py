#!/usr/bin/env python3

import sys
import re
import os
import urllib.request
import zipfile
import _myhelpers_ as myh

__description__ = "Install a Nextcloud server on Debian"
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


def configure_server(hostname, domain):
    print(f"{ci}Configuring server...{c0}")
    myh.common_config()

    phpconf = "/etc/php/7.3/apache2/php.ini"
    shutil.copy(phpconf, f"{phpconf}.o")

    with open(f"{phpconf}.o", "r") as oldf, open(phpconf, "w") as newf:
        for line in oldf:
            if "memory_limit =" in line:
                newf.write("memory_limit = 512M\n")
            elif "upload_max_filesize =" in line:
                newf.write("upload_max_filesize = 500M\n")
            elif "post_max_size =" in line:
                newf.write("post_max_size = 500M\n")
            elif "max_execution_time =" in line:
                newf.write("max_execution_time = 300\n")
            elif "date.timezone =" in line:
                newf.write("date.timezone = Europe/Paris\n")
            else:
                newf.write(line)

    for sysctl_cmd in ["enable apache2", "enable mariadb",
                       "restart apache2", "restart mariadb"]:
        os.system(f"systemctl {sysctl_cmd}")

    # TODO: Pass MySQL commands
    # - connect MySQL: "mysql -u root -p"
    # - MariaDB commands:
    #   - MariaDB [(none)]> CREATE DATABASE nextclouddb;                                 
    #   - MariaDB [(none)]> CREATE USER 'nextclouduser'@'localhost' IDENTIFIED BY 'password';
    #   - MariaDB [(none)]> GRANT ALL ON nextclouddb.* TO 'nextclouduser'@'localhost';
    #   - MariaDB [(none)]> FLUSH PRIVILEGES;
    #   - MariaDB [(none)]> EXIT;

    dlurl = "https://download.nextcloud.com/server/releases/latest.zip"
    dltgt = "/tmp/nextcloud.zip"
    urllib.request.urlretrieve(dlurl, dltgt)

    nextcloudpath = "/var/www/html/nextcloud"
    with zipfile.ZipFile(f"/tmp/{dltgt}", "r") as zipref:
        zipref.extractall(nextcloudpath)
    
    myh.recursive_chown(nextcloudpath, "www-data", "www-data")
    myh.recusive_chmod(nextcloudpath, 0o755)

    nextcloudsite = "/etc/apache2/sites-available/nextcloud.conf"
    with open(nextcloudesite, "w") as f:
        f.write("<VirtualHost *:80>\n")
        f.write(f"    ServerAdmin admin@{domain}"+"\n")
        f.write("    DocumentRoot /var/www/html/nextcloud/\n")
        f.write(f"    ServerName {hostname}.{domain}"+"\n\n")
        f.write("    Alias /nextcloud \"/var/www/html/nextcloud/\"\n\n")
        f.write("    <Directory /var/www/html/nextcloud/>\n")
        f.write("        Options +FollowSymlinks\n")
        f.write("        AllowOverride All\n")
        f.write("        Require all granted\n")
        f.write("            <IfModule mod_dav.c>\n")
        f.write("                Dav off\n")
        f.write("            </IfModule>\n")
        f.write("        SetEnv HOME /var/www/html/nextcloud\n")
        f.write("        SetEnv HTTP_HOME /var/www/html/nextcloud\n")
        f.write("    </Directory>\n\n")
        f.write("    ErrorLog ${APACHE_LOG_DIR}/error.log\n")
        f.write("    CustomLog ${APACHE_LOG_DIR}/access.log combined\n\n")
        f.write("</VirtualHost>\n")

    for enablevhost_cmd in ["a2ensite nextcloud.conf", " a2enmod rewrite",
                            "a2enmod headers", "a2enmod env", "a2enmod dir",
                            "a2enmod mime", "systemctl restart apache2"]:
        os.system(enablevhost_cmd)

    encrypt_cmd = f"certbot --apache -d {hostname.domain}"
    os.system(encrypt_cmd)
    # Answers: A, Y, 2


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

    mypkgs = ["apache2", "libapache2-mod-php", "mariadb-server", "php-xml",
              "php-cli", "php-cgi", "php-mysql", "php-mbstring",
              "php-gd php-curl", "php-zip", "python-certbot-apache"]
    myh.install_server(mypkgs)

    configure_server(myhostname, mydomain)
