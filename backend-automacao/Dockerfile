# Match the host's PC/SC 2.0.3 and the SafeSign Ubuntu 24.04 driver ABI.
FROM ubuntu:24.04

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/venv/bin:$PATH"

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
    xvfb \
    dbus-x11 \
    at-spi2-core \
    python3-pyatspi \
    default-jre \
    python3 \
    python3-venv \
    unzip \
    libatk-wrapper-java-jni \
    opensc \
    pcscd \
    pcsc-tools \
    libpcsclite1 \
    procps \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Local vendor installers are excluded from git. See docker/README.md.
COPY docker/vendor/safesign.deb /tmp/safesign.deb
RUN apt-get update && apt-get install -y /tmp/safesign.deb \
    && rm /tmp/safesign.deb && rm -rf /var/lib/apt/lists/*
COPY docker/vendor/pjeoffice.zip /tmp/pjeoffice.zip
RUN echo "6087391759c7cba11fb5ef815fe8be91713b46a8607c12eb664a9d9a6882c4c7  /tmp/pjeoffice.zip" | sha256sum -c - \
    && unzip -q /tmp/pjeoffice.zip -d /opt \
    && rm /tmp/pjeoffice.zip \
    && chmod +x /opt/pjeoffice-pro/jre/bin/java \
    && cp /usr/share/java/java-atk-wrapper.jar /opt/pjeoffice-pro/jre/lib/ext/ \
    && printf 'assistive_technologies=org.GNOME.Accessibility.AtkWrapper\n' > /opt/pjeoffice-pro/jre/lib/accessibility.properties
COPY docker/pjeoffice-pro /usr/local/bin/pjeoffice-pro
RUN chmod +x /usr/local/bin/pjeoffice-pro && python3 -m venv /opt/venv

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser dependencies and Chromium
RUN playwright install --with-deps chromium

# Keep the Django version already running before the Python 3.12 base change.
RUN pip install --no-cache-dir "Django==5.2.18"

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
