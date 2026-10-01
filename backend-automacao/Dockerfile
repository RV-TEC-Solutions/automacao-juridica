FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Install system dependencies:
# - Build tools & PostgreSQL driver
# - Xvfb (Virtual Screen in memory for Playwright & PJeOffice GUI)
# - DBus & AT-SPI2 (Accessibility framework for PJeOffice PIN typing automation)
# - Java JRE (Runtime environment for PJeOffice Pro)
# - PCSC (Smartcard / Token drivers support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    unzip \
    xvfb \
    dbus-x11 \
    at-spi2-core \
    python3-pyatspi \
    default-jre \
    pcsc-tools \
    pcscd \
    libpcsclite1 \
    procps \
    && rm -rf /var/lib/apt/lists/*



# Download e configuracao oficial do PJeOffice Pro
RUN curl -fsSL -o /tmp/pjeoffice-pro.zip "https://pje-office.pje.jus.br/pro/pjeoffice-pro-v2.5.16u-linux_x64.zip" \
    && unzip -q /tmp/pjeoffice-pro.zip -d /opt/ \
    && rm -f /tmp/pjeoffice-pro.zip \
    && chmod +x /opt/pjeoffice-pro/pjeoffice-pro.sh \
    && chmod +x /opt/pjeoffice-pro/jre/bin/* \
    && printf '#!/bin/sh\ncd /opt/pjeoffice-pro && ./pjeoffice-pro.sh "$@"\n' > /usr/local/bin/pjeoffice-pro \
    && chmod +x /usr/local/bin/pjeoffice-pro



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
