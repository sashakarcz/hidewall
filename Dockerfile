FROM python:alpine
LABEL version="3.0"
LABEL org.opencontainers.image.authors="sasha@starnix.net"

ENV PORT 80

# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR /app
COPY . /app/

# Set timezone
RUN apk add --no-cache tzdata \
 && cp /usr/share/zoneinfo/America/Chicago /etc/localtime \
 && echo "America/Chicago" > /etc/timezone

# Install dependencies
RUN apk add --no-cache \
    build-base \
    python3-dev \
    libev-dev \
    curl \
    bash

# Set display port to avoid crash
ENV DISPLAY=:99

# Upgrade pip and install requirements
RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install --no-cache-dir -r requirements.txt

CMD ["python", "yeet.py"]

