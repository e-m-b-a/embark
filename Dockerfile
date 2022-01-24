# TODO currently not supported
FROM kalilinux/kali-rolling:latest

ENV DEBIAN_FRONTEND=noninteractive
#ENV DJANGO_SETTINGS_MODULE=embark.settings
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.local/bin
# TODO add all needed vars

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
    pipenv install

EXPOSE 80
# Opening on extra port for our ASGI setup
EXPOSE 8001

ENTRYPOINT  ["./entrypoint.sh"]

