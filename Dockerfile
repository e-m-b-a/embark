# TODO currently not supported
FROM kalilinux/kali-rolling:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV DJANGO_SETTINGS_MODULE=embark.settings
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.local/bin

USER root
RUN apt-get update && apt-get -y -q --no-install-recommends install wget \
    kmod \
    procps \
    sudo \
    apt-utils \
    default-libmysqlclient-dev \
    default-mysql-client \
    build-essential \
    python3-dev \
    libssl-dev \
    swig \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

WORKDIR /app/embark

RUN /app/emba/installer.sh -D  && \
    pip3 install uwsgi -I --no-cache-dir && \
    pip3 install --user --no-warn-script-location -r /app/embark/requirements.txt

EXPOSE 80
# Opening on extra port for our ASGI setup
EXPOSE 8001

CMD  ./entrypoint.sh

