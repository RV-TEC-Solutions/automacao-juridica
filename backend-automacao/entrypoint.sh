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

# Start PJeOffice Pro in background if installed
if command -v pjeoffice-pro >/dev/null 2>&1; then
    echo "Iniciando PJeOffice Pro..."
    pjeoffice-pro &
    sleep 2
elif command -v pjeoffice >/dev/null 2>&1; then
    echo "Iniciando PJeOffice..."
    pjeoffice &
    sleep 2
fi


# Run Django database migrations
python manage.py migrate --noinput

# Run passed command
exec "$@"
