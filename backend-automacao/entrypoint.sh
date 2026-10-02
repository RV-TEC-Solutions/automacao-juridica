#!/usr/bin/env bash
set -e

# Iniciar servico DBus de sistema se disponivel
if command -v service >/dev/null 2>&1; then
    service dbus start || true
elif [ -f /var/run/dbus/system_bus_socket ]; then
    echo "DBus system bus pronto."
fi

# Inicializar DBus de sessao para integracao de acessibilidade
if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
    if command -v dbus-launch >/dev/null 2>&1; then
        eval "$(dbus-launch --sh-syntax)" || true
        export DBUS_SESSION_BUS_ADDRESS
    fi
fi

# Iniciar servidor virtual de tela Xvfb em DISPLAY=:99 se nao estiver rodando
export DISPLAY="${DISPLAY:-:99}"
if ! pgrep -x "Xvfb" > /dev/null; then
    echo "Iniciando servidor de tela virtual Xvfb em $DISPLAY..."
    Xvfb "$DISPLAY" -screen 0 1280x1024x24 -ac +extension RANDR +render -noreset &
    sleep 1
fi

# Iniciar gerenciador de janelas leve fluxbox para gerenciar foco X11
if command -v fluxbox >/dev/null 2>&1 && ! pgrep -x "fluxbox" > /dev/null; then
    echo "Iniciando gerenciador de janelas fluxbox..."
    fluxbox >/dev/null 2>&1 &
    sleep 1
fi

# Habilitar modulos de acessibilidade AT-SPI
export GTK_MODULES=gail:atk-bridge
export QT_ACCESSIBILITY=1
export AT_SPI_CLIENT=1
export NO_AT_BRIDGE=0

if [ -x /usr/libexec/at-spi-bus-launcher ]; then
    /usr/libexec/at-spi-bus-launcher --launch-immediately &
elif [ -x /usr/lib/at-spi2-core/at-spi-bus-launcher ]; then
    /usr/lib/at-spi2-core/at-spi-bus-launcher --launch-immediately &
fi

# Iniciar daemon PC/SC apenas se socket compartilhado do host nao existir
if [ ! -e /run/pcscd/pcscd.comm ] && command -v pcscd >/dev/null 2>&1 && ! pgrep -x "pcscd" > /dev/null; then
    mkdir -p /run/pcscd
    pcscd || true
fi

# Iniciar PJeOffice Pro em background se instalado
if command -v pjeoffice-pro >/dev/null 2>&1 && ! pgrep -f "pjeoffice" > /dev/null; then
    echo "Iniciando PJeOffice Pro em background..."
    pjeoffice-pro &
    sleep 3
elif command -v pjeoffice >/dev/null 2>&1 && ! pgrep -f "pjeoffice" > /dev/null; then
    echo "Iniciando PJeOffice em background..."
    pjeoffice &
    sleep 3
fi

# Aplicar migracoes do Django apenas se POSTGRES_DB estiver configurado
if [ -n "$POSTGRES_DB" ] && [ "${SKIP_MIGRATIONS:-0}" != "1" ]; then
    echo "Aplicando migrações do banco de dados..."
    python manage.py migrate --noinput || true
fi

# Executar o comando repassado ao container
exec "$@"
