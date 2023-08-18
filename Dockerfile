FROM python
LABEL version="1.0"
LABEL org.opencontainers.image.authors="sasha@starnix.net"

EXPOSE 80
WORKDIR /app
COPY . /app/

ENV PYTHONPATH "${PYTHONPATH}:/usr/src/app"

RUN ln -sf /usr/share/zoneinfo/America/Chicago /etc/localtime

RUN apt-get -qq update
RUN apt-get -qq install build-essential python3-dev libev-dev curl python-is-python3

RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install --user -r requirements.txt
CMD ["python", "yeet.py"]

