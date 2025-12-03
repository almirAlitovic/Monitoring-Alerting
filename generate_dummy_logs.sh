#!/usr/bin/env bash

LOG_DIR="/var/log/dummy"
mkdir -p "$LOG_DIR"

AUTH_LOG="$LOG_DIR/auth.log"
BOOTSTRAP_LOG="$LOG_DIR/bootstrap.log"
FONTCONFIG_LOG="$LOG_DIR/fontconfig.log"
KERN_LOG="$LOG_DIR/kern.log"
SYSLOG="$LOG_DIR/syslog"

echo "Starting dummy log generator..."
echo "Writing logs to $LOG_DIR"
echo "Press CTRL+C to stop."

generate_auth_log() {
    USERS=("root" "admin" "ubuntu" "testuser")
    IPs=("192.168.1.45" "10.0.0.12" "172.16.5.10" "185.23.14.88")

    USER=${USERS[$RANDOM % ${#USERS[@]}]}
    IP=${IPs[$RANDOM % ${#IPs[@]}]}

    case $((RANDOM % 5)) in
        0)
            echo "$(date '+%b %d %H:%M:%S') myserver sshd[1234]: Accepted password for $USER from $IP port 53726 ssh2" >> "$AUTH_LOG"
            ;;
        1)
            echo "$(date '+%b %d %H:%M:%S') myserver sshd[4321]: Failed password for invalid user $USER from $IP port 58422 ssh2" >> "$AUTH_LOG"
            ;;
        2)
            echo "$(date '+%b %d %H:%M:%S') myserver sshd[9876]: Connection closed by $IP port 42211" >> "$AUTH_LOG"
            ;;
        3)
            echo "$(date '+%b %d %H:%M:%S') myserver sudo: $USER : TTY=pts/0 ; PWD=/home/$USER ; COMMAND=/usr/bin/apt update" >> "$AUTH_LOG"
            ;;
        4)
            echo "$(date '+%b %d %H:%M:%S') myserver systemd-logind[555]: New session 42 of user $USER." >> "$AUTH_LOG"
            ;;
    esac
}

generate_bootstrap_log() {
    case $((RANDOM % 4)) in
        0)
            echo "$(date '+%Y-%m-%d %H:%M:%S') systemd: Starting Bootstrapping Services..." >> "$BOOTSTRAP_LOG"
            ;;
        1)
            echo "$(date '+%Y-%m-%d %H:%M:%S') cloud-init: running module apt-upgrade" >> "$BOOTSTRAP_LOG"
            ;;
        2)
            echo "$(date '+%Y-%m-%d %H:%M:%S') cloud-init: modules-config done at $(date)" >> "$BOOTSTRAP_LOG"
            ;;
        3)
            echo "$(date '+%Y-%m-%d %H:%M:%S') systemd: Reached target Basic System." >> "$BOOTSTRAP_LOG"
            ;;
    esac
}

generate_fontconfig_log() {
    FONTS=("Verdana" "Arial" "Roboto" "DejaVuSans" "OpenSans")
    FONT=${FONTS[$RANDOM % ${#FONTS[@]}]}

    case $((RANDOM % 4)) in
        0)
            echo "$(date '+%Y-%m-%d %H:%M:%S') fontconfig: Configuring font package: $FONT" >> "$FONTCONFIG_LOG"
            ;;
        1)
            echo "$(date '+%Y-%m-%d %H:%M:%S') fontconfig: Updating font cache..." >> "$FONTCONFIG_LOG"
            ;;
        2)
            echo "$(date '+%Y-%m-%d %H:%M:%S') fontconfig: FcDirScan done" >> "$FONTCONFIG_LOG"
            ;;
        3)
            echo "$(date '+%Y-%m-%d %H:%M:%S') fontconfig: font cache updated successfully" >> "$FONTCONFIG_LOG"
            ;;
    esac
}

generate_kern_log() {
    case $((RANDOM % 5)) in
        0)
            echo "$(date '+%b %d %H:%M:%S') myserver kernel: [$(awk 'BEGIN{srand(); print int(rand()*10000)}')] CPU0: Core temperature above threshold" >> "$KERN_LOG"
            ;;
        1)
            echo "$(date '+%b %d %H:%M:%S') myserver kernel: usb 1-1: new high-speed USB device number 4" >> "$KERN_LOG"
            ;;
        2)
            echo "$(date '+%b %d %H:%M:%S') myserver kernel: eth0: Link is Down" >> "$KERN_LOG"
            ;;
        3)
            echo "$(date '+%b %d %H:%M:%S') myserver kernel: eth0: Link is Up - 1Gbps Full Duplex" >> "$KERN_LOG"
            ;;
        4)
            echo "$(date '+%b %d %H:%M:%S') myserver kernel: EXT4-fs warning (device sda1): orphan cleanup on readonly fs" >> "$KERN_LOG"
            ;;
    esac
}

generate_syslog() {
    SERVICES=("systemd" "cron" "NetworkManager" "dbus-daemon" "avahi-daemon" "rsyslogd")

    SRV=${SERVICES[$RANDOM % ${#SERVICES[@]}]}

    case $((RANDOM % 6)) in
        0)
            echo "$(date '+%b %d %H:%M:%S') myserver $SRV[1234]: Started service successfully." >> "$SYSLOG"
            ;;
        1)
            echo "$(date '+%b %d %H:%M:%S') myserver $SRV[4321]: Reloading configuration..." >> "$SYSLOG"
            ;;
        2)
            echo "$(date '+%b %d %H:%M:%S') myserver $SRV[9876]: Warning: network latency detected" >> "$SYSLOG"
            ;;
        3)
            echo "$(date '+%b %d %H:%M:%S') myserver $SRV[1111]: Connection established" >> "$SYSLOG"
            ;;
        4)
            echo "$(date '+%b %d %H:%M:%S') myserver $SRV[2222]: Shutting down..." >> "$SYSLOG"
            ;;
        5)
            echo "$(date '+%b %d %H:%M:%S') myserver $SRV[3333]: Error: operation timed out" >> "$SYSLOG"
            ;;
    esac
}

# Loop forever
while true; do
    generate_auth_log
    generate_bootstrap_log
    generate_fontconfig_log
    generate_kern_log
    generate_syslog

    sleep 1   # adjust if you want more/less logs
done
