# Ansi Colors
ESC_SEQ="\033["
ANSI_NONE="${ESC_SEQ}39;49;00m" # Reset colors
ANSI_RED="${ESC_SEQ}1;31m"
ANSI_GREEN="${ESC_SEQ}1;32m"
ANSI_YELLOW="${ESC_SEQ}1;33m"
ANSI_CYAN="${ESC_SEQ}1;36m"

# Printing functions
printerr() {
    if [[ "$1" == "-n" ]]; then
        shift; printf "%b%s%b" "${ANSI_RED}" "$*" "${ANSI_NONE}"
    else
        printf "%b%s%b\n" "${ANSI_RED}" "$*" "${ANSI_NONE}"
    fi
}

printwarn() {
    if [[ "$1" == "-n" ]]; then
        shift; printf "%b%s%b" "${ANSI_YELLOW}" "$*" "${ANSI_NONE}"
    else
        printf "%b%s%b\n" "${ANSI_YELLOW}" "$*" "${ANSI_NONE}"
    fi
}

printdbg() {
    if [[ "$1" == "-n" ]]; then
        shift; printf "%b%s%b" "${ANSI_GREEN}" "$*" "${ANSI_NONE}"
    else
        printf "%b%s%b\n" "${ANSI_GREEN}" "$*" "${ANSI_NONE}"
    fi
}

pprint() {
    if [[ "$1" == "-n" ]]; then
        shift; printf "%b%s%b" "${ANSI_CYAN}" "$*" "${ANSI_NONE}"
    else
        printf "%b%s%b\n" "${ANSI_CYAN}" "$*" "${ANSI_NONE}"
    fi
}

# $1: command to test
# returns: 0 == true, 1 == false
cmdExists() {
    if command -v "$1" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# $1: directory to check for in PATH
# returns: 0 == found, 1 == not found
pathCheck() {
    case ":${PATH-}:" in
        *:"$1":*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# exports: $SERVICE_MANAGER
detectServiceMan() {
    INIT_PROC=$(readlink -f $(readlink -f /proc/1/exe))

    case "$INIT_PROC" in
        *systemd)
            SERVICE_MANAGER="systemd"
            ;;
        *upstart)
            SERVICE_MANAGER="upstart"
            ;;
        *runit-init)
            SERVICE_MANAGER="runit"
            ;;
        *openrc-init)
            SERVICE_MANAGER="openrc"
            ;;
        /sbin/init)
            INIT_PROC_INFO=$(/sbin/init --version 2>/dev/null | head -1)
            case "$INIT_PROC_INFO" in
                *systemd*)
                    SERVICE_MANAGER="systemd"
                    ;;
                *upstart*)
                    SERVICE_MANAGER="upstart"
                    ;;
                *runit-init*)
                    SERVICE_MANAGER="runit"
                    ;;
                *openrc-init*)
                    SERVICE_MANAGER="openrc"
                    ;;
            esac
            ;;
        *)
            SERVICE_MANAGER="sysv"
            ;;
    esac

    export SERVICE_MANAGER
}

# returns: 0 == true, nonzero otherwise
isRoot() {
    return $(id -u 2>/dev/null)
}

# $1: user to check
# returns: 0 == true, 1 == false
userExists() {
    if id -u "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}
