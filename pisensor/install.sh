#!/usr/bin/env bash

# TODO: check if root priv

# TODO: set config variables for install

# TODO: update current ip to static ip (runtime and on boot)
#ip addr change dev eth0 192.168.1.2/24
#ip route add default via 192.168.1.254
# *add static configs to /etc/dhcpcd.conf*

# TODO: install dependencies
apt-get install -y curl wget sed gawk vim perl
apt-get install -y logrotate rsyslog

apt-get install -y ffmpeg libavcodec-dev vlc mplayer

# TODO: install python dependencies

# TODO: create new user and dirs
# create shomesec user and group
mkdir -p /var/run/shomesec
# sometimes locks aren't properly removed (this seems to happen often on VM's)
rm -f /etc/passwd.lock /etc/shadow.lock /etc/group.lock /etc/gshadow.lock
useradd --system --user-group --shell /bin/false --comment "Simple Home Security" shomesec
chown -R shomesec:shomesec /var/run/shomesec

# TODO: add defaults

# TODO: add firewall settings (iptables)

# add apps to /usr/local/bin or /usr/bin

# TODO: add new services

# TODO: setup logging

# TODO: add logrotate conf

# TODO: startup services

exit 0
