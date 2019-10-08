#!/usr/bin/env bash

# TODO: add option parsing and command processing

# paths are relative to project dir
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null)
PROJECT_DIR=${PROJECT_DIR:-$(dirname $(dirname $(readlink -f "$0")))}

# import shared library funcs
. ${PROJECT_DIR}/scripts/shared_lib.sh

# sanity checks
if ! isRoot; then
    printerr "Must be run as root user" && exit 1
fi

if ! cmdExists "apt-get"; then
    printerr "Apt package manger is required" && exit 1
fi

if ! cmdExists "systemctl"; then
    printerr "Systemd service manager is required" && exit 1
fi

# TODO: set config variables for install

# install dependencies
apt-get update -y
apt-get install -y curl wget sed gawk vim perl
apt-get install -y logrotate rsyslog
apt-get install -y python python3 python3-pip python-dev

# for video server only
#apt-get install -y python-picamera python3-picamera
cat ${PROJECT_DIR}/webserver/requirements.txt | xargs -n 1 python3 -m pip install

# for web server only
#apt-get install -y ffmpeg libavcodec-dev vlc mplayer
cat ${PROJECT_DIR}/pivideo/requirements.txt | xargs -n 1 python3 -m pip install

# for sensor only
cat ${PROJECT_DIR}/pisensor/requirements.txt | xargs -n 1 python3 -m pip install

# create shomesec user and group
if ! userExists "shomesec"; then
    mkdir -p /var/run/shomesec
    # sometimes locks aren't properly removed (this seems to happen often on VM's)
    rm -f /etc/passwd.lock /etc/shadow.lock /etc/group.lock /etc/gshadow.lock
    useradd --system --user-group --shell /bin/false --comment "Simple Home Security" shomesec
    chown -R shomesec:shomesec /var/run/shomesec
fi

# TODO: add defaults

# TODO: add firewall settings (iptables)

# add apps to /usr/local/bin or /usr/bin

# TODO: add new services

# TODO: setup logging

# TODO: add logrotate conf

# TODO: startup services

exit 0
