#!/usr/bin/env bash

# Description: Install a Debian PXE server
# Author: Choops <choopsbd@gmail.com>

error="\e[31mERROR\e[0m:"
done="\e[32mDONE\e[0m:"
info="\e[36mINFO\e[0m:"

usage(){
    echo -e "USAGE: './$(basename "$0") [OPITONS]' as root or using 'sudo'"
    echo -e "\n  OPTIONS:"
    echo " -h|--help: Print this help"
}

set_hostname(){
    read -p "Hostname (or FQDN) ? " -r myhostname
    if [[ ! ${myhostname} ]]; then
        read -p "No hostname set. Keep current: '$(hostname -f)' ? [Y/n] " -rn1 keephostname
        [[ ! ${keephostname} ]] || echo
        if [[ ${keephostname} =~ [nN] ]]; then
            set_hostname
        else
            myhostname=$(hostname)
        fi
    elif [[ ${myhostname} = *[^[:alnum:].-]* ]]; then
        echo -e "${error} Hostname should be composed of alphanumeric characters and '-', separated by '.' if FQDN, but cannot start by '-' or '.'"
        set_hostname
    fi

    if [[ ${myhostname} =~ [.] ]]; then
        hostdetail="${myhostname} ${myhostname%%.*}"
        domain="${myhostname#*.}"
    else
        hostdetail="${myhostname}"
    fi
}

set_domain(){
    read -p "Domain name ? " -r domain
    if { [[ ! ${domain} = *[^[:alnum:].-]* ]] && [[ ! ${domain} =~ [.] ]] ; } \
       || [[ ${domain} = *".."* ]] || [[ ${#domain} -lt 3 ]]; then
        echo -e "${error} '${domain}' is not a valid domain name" && set_domain
    fi
    hostdetail="${myhostname}.${domain} ${myhostname}"
}

set_ip(){
    fixip=""

    dpkg -l | grep -q dnsutils || apt-get install -qq dnsutils > /dev/null

    iface=$(ip route | awk '/default/ {print$5}')
    gatewayip=$(ip route | awk '/default/ {print$3}')
    subnet=${gatewayip%.*}

    currentip=$(ip a sh "${iface}" | awk '/inet /{sub("/.*",""); print $2}')
    if (grep -qs "${iface} inet dhcp" /etc/network/interfaces); then
        read -p "IP address delivered by dhcp. Fix it ? [Y/n] " -rn1 fixip
        [[ ! ${fixip} ]] || echo
    elif (grep -qs "${iface} inet static" /etc/network/interfaces); then
        read -p "IP address already fixed. Keep current: '${currentip}' ? [Y/n] " -rn1 keepip
        [[ ! ${keepip} ]] || echo
        if [[ ! ${keepip} =~ [nN] ]]; then
            fixip=n
        fi
    fi

    if [[ ! ${fixip} =~ [nN] ]]; then
        set_fixip
    else
        ipaddr="${currentip}"
    fi
}

set_fixip(){
    read -p "IP address ? ${subnet}." -r endip
    if [[ ${endip} =~ ^[0-9]+$ ]] && [[ ${endip} -le 255 ]]; then
        ipaddr="${subnet}.${endip}"
    else
        echo -e "${error} You have to complete IP address with an integer between 1 and 254."
        set_fixip
    fi
}

add_clonezilla(){
    clonezilla_latest="2.6.4-10"   # Check latest version at https://clonezilla.org/downloads.php

    utils+=("clonezilla")
    utils_src+=("https://osdn.net/dl/clonezilla/clonezilla-live-${clonezilla_latest}-amd64.iso")
    utils_dl+=("clonezilla.iso")
    utils_menu+="\nLABEL Clonezilla\n  KERNEL clonezilla/live/vmlinuz\n  APPEND rootfstype=nfs netboot=nfs nfsroot=${ipaddr}:${tftp_root}/clonezilla initrd=clonezilla/live/initrd.img boot=live union=overlay username=user config components quiet noswap edd=on nomodeset nodmraid locales= keyboard-layouts= ocs_live_run=\"ocs-live-general\" ocs_live_extra_param=\"\" ocs_live_batch=no ip= vga=788 net.ifnames=0 nosplash i915.blacklist=yes radeonhd.blacklist=yes nouveau.blacklist=yes vmwgfw.enable_fbdev=1\n"
    more_utils+="      - Clonezilla\n"
}

add_gparted(){
    gparted_latest="1.1.0-1"    # Check latest version at https://gparted.org/download.php

    utils+=("gparted")
    utils_src+=("https://sourceforge.net/projects/gparted/files/gparted-live-stable/${gparted_latest}/gparted-live-${gparted_latest}-amd64.zip/download")
    utils_dl+=("gparted.zip")
    utils_menu+="\nLABEL Gparted\n  KERNEL gparted/vmlinuz\n  APPEND initrd=gparted/initrd.img boot=live config union=overlay username=user noswap noprompt vga=788 fetch=tftp://${ipaddr}/gparted/filesystem.squashfs\n"
    more_utils+="      - Gparted\n"
}

add_memtest(){
    memtest_latest="5.01"       # Check latest version at http://www.memtest.org

    utils+=("memtest")
    utils_src+=("http://www.memtest.org/download/${memtest_latest}/memtest86+-${memtest_latest}.zip")
    utils_dl+=("memtest.zip")
    utils_menu+="\nLABEL Memtest86+\n  KERNEL memtest\n"
    more_utils+="      - Memtest86+\n"
}

set_utilities(){
    utils=()
    utils_src=()
    utils_dl=()
    utils_menu=""
    more_utils=""

    echo "Add utilities among:"
    echo "  1) Clonezzilla"
    echo "  2) Gparted"
    echo "  3) Memmtest86+"
    read -p "Your choice ['1 2' for multiple choices, 'a' for all, or just press <Enter> for none] ? " -ra utilities
    if [[ ${#utilities[@]} -gt 0 ]]; then
        more_utils+="    - \e[36mUtilities\e[0m:\n"
        if [[ ${#utilities[@]} -eq 1 ]] && [[ ${utilities[0]} = a ]]; then
            add_clonezilla
            add_gparted
            add_memtest
        else
            for utility in "${utilities[@]}"; do
                case ${utility} in
                    1) add_clonezilla ;;
                    2) add_gparted ;;
                    3) add_memtest ;;
                    *) echo -e "${error} Invalid choice" && set_utilities
                esac
            done
        fi
    fi
}

add_stable(){
    netboots+=("${stable}")
    netboots_src+=("http://ftp.nl.debian.org/debian/dists/${stable}/main/installer-amd64/current/images/netboot/netboot.tar.gz")
    netboots_menu+="\nLABEL Debian stable (${stable})\n  KERNEL ${stable}/debian-installer/amd64/linux\n  APPEND initrd=${stable}/debian-installer/amd64/initrd.gz vga=788 ramdisk_size=9372 root=/dev/rd/0 devfs=mount,dall rw --\n"
    more_netboots+="      - Debian stable (${stable})\n"
}

add_oldstable(){
    netboots+=("${oldstable}")
    netboots_src+=("http://ftp.nl.debian.org/debian/dists/${oldstable}/main/installer-amd64/current/images/netboot/netboot.tar.gz")
    netboots_menu+="\nLABEL Debian oldstable (${oldstable})\n  KERNEL ${oldstable}/debian-installer/amd64/linux\n  APPEND initrd=${oldstable}/debian-installer/amd64/initrd.gz vga=788 ramdisk_size=9372 root=/dev/rd/0 devfs=mount,dall rw --\n"
    more_netboots+="      - Debian oldstable (${oldstable})\n"
}

add_ublts(){
    netboots+=("${ublts}")
    netboots_src+=("http://archive.ubuntu.com/ubuntu/dists/${ublts}/main/installer-amd64/current/legacy-images/netboot/netboot.tar.gz")
    #netboots_src+=("http://archive.ubuntu.com/ubuntu/dists/${ublts}-updates/main/installer-amd64/current/images/netboot/netboot.tar.gz")
    netboots_menu+="\nLABEL Ubuntu ${ubltsv} (${ublts})\n  KERNEL ${ublts}/ubuntu-installer/amd64/linux\n  APPEND initrd=${ublts}/ubuntu-installer/amd64/initrd.gz vga=788 locale=fr_FR.UTF-8;keyboard-configuration/layoutcode=fr"
    more_netboots+="      - Ubuntu ${ubltsv} LTS (${ublts})\n"
}

set_installers(){
    netboots=()
    netboots_src=()
    netboots_menu=""
    more_netboots=""

    stable=buster
    oldstable=stretch
    ublts=focal
    ubltsv="20.04"

    echo "Add installers among:"
    echo "  1) Debian stable (${stable})"
    echo "  2) Debian oldstable (${oldstable})"
    echo "  3) Ubuntu ${ubltsv} LTS (${ublts})"
    read -p "Your choice ['1 2' for multiple choices, 'a' for all, or just press <Enter> for none] ? " -ra installers
    if [[ ${#installers[@]} -gt 0 ]]; then
        more_netboots+="    - \e[36mInstallers\e[0m:\n"
        if [[ ${#installers[@]} -eq 1 ]] && [[ ${installers[0]} = a ]]; then
            add_stable
            add_oldstable
            add_ublts
        else
            for installer in "${installers[@]}"; do
                case ${installer} in
                    1) add_stable ;;
                    2) add_oldstable ;;
                    3) add_ublts ;;
                    *) echo -e "${error} Invalid choice" && set_installers
                esac
            done
        fi
    fi
}

set_server(){
    domain=""

    set_hostname
    [[ ! ${domain} ]] && set_domain
    set_ip

    tftp_root=/srv/tftp

    read -p "PXE title [default '${domain} PXE Boot'] ? " -r pxe_title
    [[ ! ${pxe_title} ]] && pxe_title="${domain} PXE Boot"

    more_menus=""
    set_utilities
    more_menus+="${more_utils}"
    set_installers
    more_menus+="${more_netboots}"

    echo -e "\e[36mSettings\e[0m:"
    echo -e "  - \e[36mHostname\e[0m: ${myhostname%%.*}"
    echo -e "  - \e[36mDomain name\e[0m: ${domain}"
    [[ ! ${fixip} =~ [nN] ]] && echo -e "  - \e[36mIP address\e[0m: ${ipaddr}"
    echo -e "  - \e[36mPXE settings\e[0m:"
    echo -e "    - \e[36mTitle\e[0m: ${pxe_title}"
    echo -ne "${more_menus}"

    read -p "Confirm configuration [Y/n] ? " -rn1 confirmconf
    [[ ! ${confirmconf} ]] || echo
    if [[ ${confirmconf} =~ [nN] ]]; then
        set_server
    fi
}

deploy_clonezilla(){
    partimag_folder=/home/partimag

    mount -o loop -t iso9660 clonezilla.iso /mnt

    [[ -d ${tftp_root}/clonezilla ]] && rm -rf "${tftp_root}"/clonezilla
    mkdir -p "${tftp_root}"/clonezilla
    cp -ar /mnt/* "${tftp_root}"/clonezilla

    umount /mnt
    rm -f clonezilla.iso

    mkdir -p "${partimag_folder}"
    chmod 777 "${partimag_folder}"

    for nfs_share in "${tftp_root}/clonezilla" "${partimag_folder}"; do
        nfs_opt="rw,async,no_wdelay,root_squash,insecure_locks,no_subtree_check"
        grep -iqs "${nfs_share}" /etc/exports || echo "${nfs_share} *(${nfs_opt})" >>/etc/exports
    done
    systemctl restart nfs-kernel-server
}

deploy_gparted(){
    [[ -d gparted ]] && rm -rf gparted
    mkdir -p gparted

    7z x gparted.zip -ogparted > /dev/null

    [[ -d "${tftp_root}"/gparted ]] && rm -rf "${tftp_root}"/gparted
    mkdir -p "${tftp_root}"/gparted
    cp gparted/live/{initrd.img,vmlinuz,filesystem.squashfs} "${tftp_root}"/gparted/

    rm -rf gparted
    rm -f gparted.zip
}

deploy_memtest(){
    7z x memtest.zip > /dev/null
    
    mv "memtest86+-${memtest_latest}".bin "${tftp_root}"/memtest
    chmod 755 "${tftp_root}"/memtest

    rm -f memtest.zip
}

install_server(){
    sed -e 's/main$/main contrib non-free/g' -e '/cdrom/d' -e '/#.$/d' -e '/./,$!d' \
        -i /etc/apt/sources.list
    apt update
    apt full-upgrade -y 2>/dev/null

    echo "${myhostname%%.*}" > /etc/hostname
    sed "s/^127.0.1.1.*/127.0.1.1\t${hostdetail}/" -i /etc/hosts
    hostname "${myhostname}"

    if [[ ! ${fixip} =~ [nN] ]]; then
        if (grep -qs "${iface} inet dhcp" /etc/network/interfaces); then
            sed "s|iface ${iface} inet dhcp|iface ${iface} inet static\n    address ${ipaddr}/24\n    gateway ${gatewayip}|" -i /etc/network/interfaces
        elif (grep -qs "${iface} inet static" /etc/network/interfaces); then
            sed "/iface ${iface}/{N;s|.*|iface ${iface} inet static\n    address ${ipaddr}/24|}" -i /etc/network/interfaces
        fi
        ip link set "${iface}" down
        ip addr del "${currentip}"/24 dev "${iface}"
        ip addr add "${ipaddr}"/24 dev "${iface}"
        ip link set "${iface}" up
        ip route add default via "${gatewayip}"
    fi

    apt install -y vim ssh git curl build-essential p7zip-full tree htop neofetch rsync \
        tftpd-hpa syslinux-utils syslinux pxelinux nfs-kernel-server \
        2>/dev/null

    mapfile -t residualconf < <(dpkg -l | awk '/^rc/ {print $2}')
    [[ ${#residualconf[@]} -gt 0 ]] && apt purge -y "${residualconf[@]}" 2>/dev/null

    apt autoremove --purge -y 2>/dev/null
    apt autoclean 2>/dev/null
    apt clean 2>/dev/null

    swapconf=/etc/sysctl.d/99-swappiness.conf
    if ! (grep -qs 'vm.swappiness=5' "${swapconf}"); then
        echo vm.swappiness=5 >>"${swapconf}"
        echo vm.vfs_cache_pressure=50 >>"${swapconf}"
        sysctl -p "${swapconf}"
        swapoff -av
        swapon -av
    fi

    sshconf=/etc/ssh/sshd_config
    if ! (grep -qs "^PermitRootLogin yes" "${sshconf}"); then
        sed 's/^#PermitRootLogin.*/PermitRootLogin yes/' -i "${sshconf}"
    fi
    systemctl restart ssh

    mkdir -p "${tftp_root}"

    sed -e "s|\${tftp_root}|${tftp_root}|" \
        -e "s|\${ipaddr}|${ipaddr}|" \
        "${confpath}"/pxe/tftpd-hpa > /etc/default/tftpd-hpa

    systemctl enable tftpd-hpa
    systemctl restart tftpd-hpa

    cp /usr/lib/syslinux/modules/bios/{chain.c32,mboot.c32,menu.c32,reboot.c32,vesamenu.c32,libcom32.c32,libutil.c32,ldlinux.c32,poweroff.c32} -t "${tftp_root}"/
    cp /usr/lib/PXELINUX/pxelinux.0 "${tftp_root}"/
    chmod 755 "${tftp_root}"/*

    sed -e "s|\${iface}|${iface}|" \
        -e "s|\${ipaddr}|${ipaddr}|" \
        -e "s|\${tftp_root}|${tftp_root}|" \
        -e "s|\${domain}|${domain}|" \
        "${confpath}"/pxe/pxe.conf > /etc/pxe.conf

    mkdir -p "${tftp_root}"/pxelinux.cfg

    pxe_bg='bg_image.png'
    cp "${resourcespath}"/img/debian_bg.png "${tftp_root}/${pxe_bg}"

    sed -e "s|\${pxe_bg}|${pxe_bg}|" \
        -e "s|\${pxe_title}|${pxe_title}|" \
        "${confpath}"/pxe/menu_default > "${tftp_root}"/pxelinux.cfg/default

    if [[ ${#utils[@]} -gt 0 ]]; then
        grep -qs pxelinux.cfg/utilities "${tftp_root}/pxelinux.cfg/default" || \
            echo -e "LABEL Utilities\nKERNEL vesamenu.c32\nAPPEND pxelinux.cfg/utilities" >> "${tftp_root}"/pxelinux.cfg/default

        for i in $(seq 0 $((${#utils[@]}-1))); do
            [[ -f ${utils_dl[$i]} ]] || wget "${utils_src[$i]}" -O "${utils_dl[$i]}"
            deploy_"${utils[$i]}"
        done

        sed -e "s|\${pxe_bg}|${pxe_bg}|" \
            -e "s|\${pxe_title}|${pxe_title}|" \
            -e "s|\${utils_menu}|${utils_menu}|" \
            "${confpath}"/pxe/menu_utilities > "${tftp_root}"/pxelinux.cfg/utilities
    fi

    if [[ ${#netboots[@]} -gt 0 ]]; then
        grep -qs pxelinux.cfg/install "${tftp_root}"/pxelinux.cfg/default || \
            echo -e "LABEL Install\nKERNEL vesamenu.c32\nAPPEND pxelinux.cfg/install" >> "${tftp_root}"/pxelinux.cfg/default
        
        for i in $(seq 0 $((${#netboots[@]}-1))); do
            [[ -f ${netboots[$i]}-netboot.tar.gz ]] || wget "${netboots_src[$i]}" -O "${netboots[$i]}"-netboot.tar.gz
            if [[ -d ${tftp_root}/${netboots[$i]} ]]; then
                rm -rf "${tftp_root:?}/${netboots[$i]}"
            fi
            mkdir -p "${tftp_root}/${netboots[$i]}"
            tar xfz "${netboots[$i]}"-netboot.tar.gz -C "${tftp_root}/${netboots[$i]}"/
            rm -rf "${netboots[$i]}"-netboot.tar.gz
        done

        sed -e "s|\${pxe_bg}|${pxe_bg}|" \
            -e "s|\${pxe_title}|${pxe_title}|" \
            -e "s|\${netboots_menu}|${netboots_menu}|" \
            "${confpath}"/pxe/menu_install > "${tftp_root}"/pxelinux.cfg/install
    fi
}

tweak_root_config(){
    for oldfile in /root/.vim{rc,info}; do
        rm -f "${oldfile}"
    done

    for element in "${gitpath}"/root/*; do
        rm -rf /root/."$(basename ${element})"
        cp -r "${element}" /root/."$(basename ${element})"
    done
    curl -sfLo /root/.vim/autoload/plug.vim --create-dirs \
        https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim

    vim +PlugInstall +qall
}

gitpath="$(dirname "$(realpath "$0")")"
confpath="${gitpath}"/conf

[[ $(lsb_release -si) != Debian ]] && echo -e "${error} Your OS is not debian" && exit 1

[[ $(whoami) != root ]] && echo -e "${error} Need higher privileges" && usage && exit 1

[[ $# -gt 1 ]] && echo -e "${error} Too many arguments" && usage && exit 1

if [[ $# -eq 1 ]]; then
    if [[ $1 =~ ^(-h|--help)+$ ]]; then
        usage && exit 0
    else
        echo -e "${error} Bad argument" && usage && exit 1
    fi
fi

set_server
install_server
tweak_root_config

echo -e "${done} Installation finished"
read -p "Reboot now [Y/n] ? " -rn1 reboot
[[ ! ${reboot} ]] || echo
[[ ! ${reboot} =~ [nN] ]] && reboot
