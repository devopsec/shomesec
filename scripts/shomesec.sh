#!/usr/bin/env bash

function printUsage() {
    printf '%s\n\n' "USAGE: ${BASH_ARGV[-1]} <command> [options]"
    printf '\t%s\t%s\n' "COMMAND" "OPTIONS"
    printf '\t%s\t%s\n' "install" "<ardsensor|pipanel|pisensor|webserver>"
    printf '\t%s\t%s\n' "help" ""
}

# parse cli args / options
case "$1" in
    install)
        shift
        case "$1" in
            ardsensor)
                INSTALL_ARDSENSOR=1
                ;;
            pipanel)
                INSTALL_PIPANEL=1
                ;;
            pisensor)
                INSTALL_PISENSOR=1
                ;;
            webserver)
                INSTALL_WEBSERVER=1
                ;;
            *)
                printerr "Invalid options for install command"
                printUsage
                exit 1
                ;;
        esac
        ;;
    help)
        printUsage
        exit 0
        ;;
    *)
        printerr "Command not recognized"
        printUsage
        exit 1
esac

# paths are relative to project dir
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null)
PROJECT_DIR=${PROJECT_DIR:-$(dirname $(dirname $(readlink -f "$0")))}

# import shared library funcs
. ${PROJECT_DIR}/scripts/shared_lib.sh

function preInstallSanityChecks() {
    if ! isRoot; then
        printerr "Must be run as root user"
        exit 1
    fi
    if ! cmdExists "apt-get"; then
        printerr "Apt package manger is required"
        exit 1
    fi
    if ! cmdExists "systemctl"; then
        printerr "Systemd service manager is required"
        exit 1
    fi
}

function createShomesecUserGroup() {
    if ! userExists "shomesec"; then
        mkdir -p /run/shomesec
        # sometimes locks aren't properly removed (this seems to happen often on VM's)
        rm -f /etc/passwd.lock /etc/shadow.lock /etc/group.lock /etc/gshadow.lock
        useradd --system --user-group --shell /bin/false --comment "Simple Home Security" shomesec
        chown -R shomesec:shomesec /run/shomesec
    fi
}

# for shomesec control panel
# TODO: finish this
if (( ${INSTALL_ARDSENSOR:-0} == 1 )); then
    printerr "not yet implemented"
    exit 1
fi

# for arduino sensor w/ video server
# TODO: finish this
if (( ${INSTALL_PIPANEL:-0} == 1 )); then
    printerr "not yet implemented"
    exit 1
fi

# for raspberry pi sensor w/ video server
if (( ${INSTALL_PISENSOR:-0} == 1 )); then
    # requirements for both modules
    apt-get update -y
    apt-get install -y curl wget sed gawk vim perl logrotate rsyslog python python3 python3-pip python-dev python-setuptools python3-setuptools
    createShomesecUserGroup
    usermod -a -G gpio,kmem,video shomesec

    # configure pisensor
    python3 -m pip install ${PROJECT_DIR}/pisensor/requirements.txt

    touch /etc/default/shomesec/pisense.conf
    cp -f ${PROJECT_DIR}/pisensor/pisense.service /lib/systemd/system/pisense.service
    systemctl daemon-reload
    systemctl enable pisense

    # configure pivideo
    apt-get install -y python-picamera python3-picamera
    python3 -m pip install ${PROJECT_DIR}/pivideo/requirements.txt

    touch /etc/default/shomesec/pivid.conf
    cp -f ${PROJECT_DIR}/pivideo/pivid.service /lib/systemd/system/pivid.service
    systemctl daemon-reload
    systemctl enable pivid

    # startup services and validate they didn't crash
    systemctl restart pisense
    systemctl restart pivid
    if systemctl is-active --quiet pisense && systemctl is-active --quiet pivid; then
        pprint "successfully installed shomesec raspberry pi sensor"
        exit 0
    else
        printerr "error occurred installing shomesec raspberry pi sensor"
        exit 1
    fi
fi

# for shomesec web server
if (( ${INSTALL_WEBSERVER:-0} == 1 )); then
    # requirements for this module
    apt-get update -y
    apt-get install -y curl wget sed gawk vim perl logrotate rsyslog python python3 python3-pip python-dev python-setuptools python3-setuptools
    apt-get install -y ffmpeg libavcodec-dev vlc mplayer uwsgi uwsgi-emperor uwsgi-plugin-python3 nginx-full
    python3 -m pip install ${PROJECT_DIR}/webserver/requirements.txt
    createShomesecUserGroup

    # configure web server
    # TODO: create TLS certs (letsencrypt or self-signed)
    # TODO: configure nginx configs (defaults and our site)
    touch /etc/default/shomesec/pyserve.conf
    cp -f ${PROJECT_DIR}/webserver/pyserve.service /lib/systemd/system/pyserve.service
    systemctl daemon-reload
    systemctl enable pyserve

    # startup services and validate they didn't crash
    systemctl restart pyserve
    if systemctl is-active --quiet pyserve; then
        pprint "successfully installed shomesec web server"
        exit 0
    else
        printerr "error occurred installing shomesec web server"
        exit 1
    fi
fi

# TODO: add firewall settings (iptables)

# add apps to /usr/local/bin or /usr/bin

# TODO: setup logging

# TODO: add logrotate conf
