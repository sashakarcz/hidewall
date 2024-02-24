FROM python
LABEL version="2.0"
LABEL org.opencontainers.image.authors="sasha@starnix.net"

ENV PORT 80

# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR /app
COPY . /app/

RUN ln -sf /usr/share/zoneinfo/America/Chicago /etc/localtime

RUN apt-get -qq update
RUN apt-get -qq install build-essential python3-dev libev-dev curl python-is-python3

# Install Google Chrome for webdriver fun
RUN apt-get update && \
    apt-get install -y wget gnupg curl && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable

# Set display port to avoid crash
ENV DISPLAY=:99

RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install --no-cache-dir -r requirements.txt
CMD ["python", "yeet.py"]

