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
    xvfb \
    dbus-x11 \
    at-spi2-core \
    python3-pyatspi \
    default-jre \
    pcscd \
    libpcsclite1 \
    procps \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

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
