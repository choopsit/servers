#!/usr/bin/env bash

set -e

c0="\e[0m"
ce="\e[31m"
cf="\e[32m"

error="${ce}Error${c0}:"
done="${cf}Done${c0}:"

setnewname(){
    read -p "New name ? " -r newname
    [[ ! ${newname} ]] && echo -e "${error} No hostname given" && setnewname
    if [[ ! ${newname} =~ ^[a-z0-9]*[a-z0-9-]*[a-z0-9]$ ]]; then
        echo -e "${error} '${newname}' is not a valid hostname" && setnewname
    fi
}

myserver="192.168.10.2"

read -p "Erase disk to put clone ? [Y/n] " -rn1 clone
[[ ! ${clone} ]] || echo
[[ ${clone} =~ [nN] ]] && reboot

[[ $USER = root ]] || pow=sudo

# TODO: find another way to determine old name... can be based on ocs-inventory and MAC address
for dev in /dev/sda1 /dev/vda1; do
    if [[ -e ${dev} ]]; then
        echo $dev
        "${pow}" mount "${dev}" /mnt
        [[ -f /mnt/etc/hostname ]] && oldname="$(cat /mnt/etc/hostname)"
        "${pow}" umount /mnt
    fi
done

if [[ ${oldname} ]]; then
    read -p "Keep old name: '${oldname}' ? [Y/n] " -rn1 keepohn
    [[ ! ${keepohn} ]] || echo
    if [[ ${keepohn} =~ [nN] ]]; then
        setnewname
    else
        newname="${oldname}"
    fi
else
    setnewname
fi

echo "${newname}" >/tmp/NEWCOMPUTERNAME
