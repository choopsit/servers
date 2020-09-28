#!/usr/bin/env bash

# Description: Install a Debian Saltstack master
# Author: Choops <choopsbd@gmail.com>

c0="\e[0m"
ce="\e[31m"
cf="\e[32m"
ci="\e[36m"

error="${ce}Error${c0}:"
done="${cf}Done${c0}:"

usage(){
    echo -e "${ci}Usage${c0}:"
    echo "  './$(basename "$0") [OPITONS]' as root or using 'sudo'"
    echo -e "${ci}Options${c0}:"
    echo "  -h|--help: Print this help"
}

salt_hostname(){
    echo "Your server is named 'salt' (good for you)"
    read -p "Keep it ? [Y/n] " -rn1 keephn
    [[ ! ${keephn} ]] || echo
    [[ ${keephn} =~ [nN] ]] && set_hostname
    myhostname="$(hostname -f)"
    if [[ ${myhostname} =~ [.] ]]; then
        hostdetail="${myhostname} ${myhostname%%.*}"
        domain="${myhostname#*.}"
        echo "Your domain name is '${domain}'"
        read -p "Keep it ? [Y/n] " -rn1 keepdn
        [[ ! ${keepdn} ]] || echo
        [[ ${keepdn} =~ [nN] ]] && unset domain
    fi
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
    unset fixip

    iface=$(ip route | awk '/default/ {print$5}')
    gatewayip=$(ip route | awk '/default/ {print$3}')
    subnet=${gatewayip%.*}

    currentip=$(ip a sh "${iface}" | awk '/inet /{sub("/.*",""); print $2}')
    if grep -qs "${iface} inet dhcp" /etc/network/interfaces; then
        read -p "IP address delivered by dhcp. Fix it ? [Y/n] " -rn1 fixip
        [[ ! ${fixip} ]] || echo
    elif grep -qs "${iface} inet static" /etc/network/interfaces; then
        read -p "IP address already fixed. Keep current: '${currentip}' ? [Y/n] " -rn1 keepip
        [[ ! ${keepip} ]] || echo
        [[ ! ${keepip} =~ [nN] ]] && fixip=n
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

set_server(){
    unset domain

    if [[ $(hostname -s) = salt ]]; then
        salt_hostname
    else
        set_hostname
    fi

    [[ ! ${domain} ]] && set_domain
    set_ip

    echo -e "${ci}Settings${c0}:"
    echo -e "  - ${ci}Hostname${c0}: ${myhostname%%.*}"
    echo -e "  - ${ci}Domain name${c0}: ${domain}"
    [[ ! ${fixip} =~ [nN] ]] && echo -e "  - ${ci}IP address${c0}: ${ipaddr}"

    read -p "Confirm configuration [Y/n] ? " -rn1 confirmconf
    [[ ! ${confirmconf} ]] || echo
    [[ ${confirmconf} =~ [nN] ]] && set_server
}

fix_ipaddr(){
    if grep -qs "${iface} inet dhcp" /etc/network/interfaces; then
        sed "s|iface ${iface} inet dhcp|iface ${iface} inet static\n    address ${ipaddr}/24\n    gateway ${gatewayip}|" -i /etc/network/interfaces
    elif grep -qs "${iface} inet static" /etc/network/interfaces; then
        sed "/iface ${iface}/{N;s|.*|iface ${iface} inet static\n    address ${ipaddr}/24|}" -i /etc/network/interfaces
    fi
    ip link set "${iface}" down
    ip addr del "${currentip}"/24 dev "${iface}"
    ip addr add "${ipaddr}"/24 dev "${iface}"
    ip link set "${iface}" up
    ip route add default via "${gatewayip}"
}

install_server(){
    echo "${myhostname%%.*}" >/etc/hostname
    sed "s/^127.0.1.1.*/127.0.1.1\t${hostdetail}/" -i /etc/hosts
    hostname "${myhostname}"

    if [[ ! ${fixip} =~ [nN] ]]; then
        fix_ipaddr
    fi

    sed 's/main$/main contrib non-free/g; /cdrom/d; /#.$/d; /./,$!d' \
        -i /etc/apt/sources.list

    wget -O - https://repo.saltstack.com/py3/debian/"${stablev}"/amd64/latest/SALTSTACK-GPG-KEY.pub | apt-key add -
    echo "deb http://repo.saltstack.com/py3/debian/${stablev}/amd64/latest ${stable} main" >/etc/apt/sources.list.d/saltstack.list

    apt update
    apt full-upgrade -y 2>/dev/null

    apt install -y vim ssh git curl build-essential p7zip-full tree htop neofetch rsync \
        salt-master salt-api salt-ssh \
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
    grep -qs "^PermitRootLogin yes" "${sshconf}" || \
        sed 's/^#PermitRootLogin.*/PermitRootLogin yes/' -i "${sshconf}"

    systemctl restart ssh

    mkdir -p /srv/{salt,pillar}

    systemctl restart salt-master
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

positionals=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage && exit 0 ;;
        -*)
            echo -e "${error} Unknown option '$1'" && usage && exit 1 ;;
        *)
            positionals+=("$1") ;;
    esac
    shift
done

[[ ${#positionals[@]} -gt 0 ]] &&
    echo -e "${error} Bad argument(s) '${positionals[@]}'" && usage && exit 1

[[ $(lsb_release -si) != Debian ]] && echo -e "${error} Your OS is not debian" && exit 1
[[ $(whoami) != root ]] && echo -e "${error} Need higher privileges" && usage && exit 1

gitpath="$(dirname "$(realpath "$0")")"
confpath="${gitpath}"/conf

stable=buster
stablev=10

set_server
install_server
tweak_root_config

echo -e "${done} Installation finished"
read -p "Reboot now [Y/n] ? " -rn1 reboot
[[ ! ${reboot} ]] || echo
[[ ! ${reboot} =~ [nN] ]] && reboot
