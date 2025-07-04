# Use a Debian-based slim Python image for better compatibility
FROM python:3.9-slim-buster
LABEL version="4.0"
LABEL org.opencontainers.image.authors="sasha@starnix.net"

ENV PORT 80

# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR /app
COPY . /app/

# Set timezone
# For Debian-based images, tzdata package is usually sufficient
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && cp /usr/share/zoneinfo/America/Chicago /etc/localtime \
    && echo "America/Chicago" > /etc/timezone

# Install build dependencies required for some Python packages
# (e.g., those with C extensions, like grpcio for opentelemetry-exporter-otlp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libev-dev \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Set display port to avoid crash (if X server related, usually not needed for web apps)
ENV DISPLAY=:99

# Upgrade pip and install requirements
RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install --no-cache-dir -r requirements.txt

# Command to run your Flask app
CMD ["python", "yeet.py"]
