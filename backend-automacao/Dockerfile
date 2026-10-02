FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV DOCKER_CONTAINER=1

# Install system dependencies:
# - Build tools & PostgreSQL driver
# - Xvfb (Virtual Screen in memory for Playwright & PJeOffice GUI)
# - Fluxbox (Lightweight window manager to ensure proper X11 window focus & lifecycle)
# - X11 automation tools (xdotool, wmctrl, x11-utils for direct GUI PIN typing)
# - DBus & AT-SPI2 (Accessibility framework for PJeOffice PIN typing automation)
# - Java JRE (Runtime environment for PJeOffice Pro) + ATK Wrapper for Java
# - PCSC (Smartcard / Token drivers support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    unzip \
    xvfb \
    fluxbox \
    xdotool \
    wmctrl \
    x11-utils \
    dbus-x11 \
    at-spi2-core \
    python3-pyatspi \
    libatk-wrapper-java \
    libatk-wrapper-java-jni \
    default-jre \
    pcsc-tools \
    pcscd \
    libpcsclite1 \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Download e instalacao oficial do PJeOffice Pro
RUN curl -fsSL -o /tmp/pjeoffice-pro.zip "https://pje-office.pje.jus.br/pro/pjeoffice-pro-v2.5.16u-linux_x64.zip" \
    && unzip -q /tmp/pjeoffice-pro.zip -d /opt/ \
    && rm -f /tmp/pjeoffice-pro.zip \
    && chmod +x /opt/pjeoffice-pro/pjeoffice-pro.sh \
    && chmod +x /opt/pjeoffice-pro/jre/bin/* \
    && printf '#!/bin/sh\ncd /opt/pjeoffice-pro && ./pjeoffice-pro.sh "$@"\n' > /usr/local/bin/pjeoffice-pro \
    && chmod +x /usr/local/bin/pjeoffice-pro

# Garantir que assistive_technologies esteja desativado no Java para evitar erro AWTError no Debian
RUN find /etc /usr/lib/jvm /opt/pjeoffice-pro -name "accessibility.properties" -exec sed -i 's/^assistive_technologies=/#assistive_technologies=/' {} \; 2>/dev/null || true

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser dependencies and Chromium
RUN playwright install --with-deps chromium

# Copy entrypoint script and source code
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

COPY . .

# Expose backend service port
EXPOSE 8007

# Set entrypoint to initialize Xvfb, DBus, and AT-SPI before starting application
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command starts Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8007"]
