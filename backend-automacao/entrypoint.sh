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
if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    display_number="${DISPLAY#:}"
    display_number="${display_number%%.*}"
    rm -f "/tmp/.X${display_number}-lock" "/tmp/.X11-unix/X${display_number}"
    echo "Iniciando servidor de tela virtual Xvfb em $DISPLAY..."
    Xvfb "$DISPLAY" -screen 0 1280x1024x24 -ac +extension RANDR +render -noreset &
    for attempt in 1 2 3 4 5 6 7 8 9 10; do
        xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 && break
        sleep 1
    done
    if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
        echo "Xvfb não ficou disponível em $DISPLAY." >&2
        exit 1
    fi
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

# Iniciar daemon PC/SC apenas se socket ativo compartilhado do host nao existir
if command -v pcscd >/dev/null 2>&1 && ! pgrep -x "pcscd" > /dev/null; then
    if [ ! -S /run/pcscd/pcscd.comm ]; then
        echo "Iniciando daemon PC/SC local..."
        mkdir -p /run/pcscd
        rm -f /run/pcscd/pcscd.comm /run/pcscd/pcscd.pid
        pcscd || true
        sleep 1
    else
        echo "Socket PC/SC do host detectado em /run/pcscd/pcscd.comm."
    fi
fi

# Iniciar PJeOffice Pro em background se instalado
if [ -n "${PJE_PKCS11_MODULES:-}" ]; then
    mkdir -p /root/.pjeoffice-pro
    pje_config=/root/.pjeoffice-pro/pjeoffice-pro.config
    if [ -f "$pje_config" ]; then
        sed -i '/^list\.a3=/d' "$pje_config"
    fi
    printf 'list.a3=%s\n' "$PJE_PKCS11_MODULES" >> "$pje_config"
fi

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

    echo "Garantindo usuário e fontes iniciais se banco estiver vazio..."
    python manage.py configurar_app --if-empty \
        --username "${INITIAL_ADMIN_USER:-admin}" \
        --name "${INITIAL_ADMIN_NAME:-Administrador}" \
        --password "${INITIAL_ADMIN_PASSWORD:-admin}" || true
fi

# Executar o comando repassado ao container
exec "$@"
