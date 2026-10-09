#!/usr/bin/env bash
set -e

# Start DBus service for AT-SPI accessibility bus communication
if command -v service >/dev/null 2>&1; then
    service dbus start || true
elif [ -f /var/run/dbus/system_bus_socket ]; then
    echo "DBus system bus socket ready."
fi

# Start Xvfb (Virtual Framebuffer Display) on DISPLAY=:99 if not already running
export DISPLAY="${DISPLAY:-:99}"
if ! pgrep -x "Xvfb" > /dev/null; then
    echo "Iniciando servidor de tela virtual Xvfb em $DISPLAY..."
    Xvfb "$DISPLAY" -screen 0 1280x1024x24 -ac &
    sleep 2
fi

# Enable AT-SPI accessibility modules for PJeOffice GUI interaction
export GTK_MODULES=gail:atk-bridge
export QT_ACCESSIBILITY=1
export AT_SPI_CLIENT=1
export NO_AT_BRIDGE=0

# Keep Chrome, Java and the PIN helper on the same accessibility session.
if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
    eval "$(dbus-launch --sh-syntax)"
fi

# Start PJeOffice Pro in background if installed
if [ "${PJE_OFFICE_ENABLED:-false}" = "true" ] && command -v pjeoffice-pro >/dev/null 2>&1; then
    mkdir -p /root/.pjeoffice-pro
    if [ ! -f /root/.pjeoffice-pro/pjeoffice-pro.config ]; then
        driver=$(find /usr/lib -maxdepth 1 -name 'libaetpkss.so.*' | sort | tail -n 1)
        printf 'list.a3=%s\n' "$driver" > /root/.pjeoffice-pro/pjeoffice-pro.config
    fi
    echo "Iniciando PJeOffice Pro..."
    pjeoffice-pro > /tmp/pjeoffice-startup.log 2>&1 &
    pjeoffice_pid=$!
    sleep 2
    if ! kill -0 "$pjeoffice_pid" 2>/dev/null; then
        cat /tmp/pjeoffice-startup.log >&2
        echo "PJeOffice Pro não iniciou." >&2
        exit 1
    fi
elif [ "${PJE_OFFICE_ENABLED:-false}" = "true" ] && command -v pjeoffice >/dev/null 2>&1; then
    echo "Iniciando PJeOffice..."
    pjeoffice &
    sleep 2
fi


# Run Django database migrations
python manage.py migrate --noinput

# Run passed command
exec "$@"
