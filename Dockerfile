FROM kalilinux/kali-rolling:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV DJANGO_SETTINGS_MODULE=embark.settings.deploy
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.local/bin
# TODO add all needed vars that are not in the .env

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
    pipenv \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /var/www
# * use emba from host or copy [root]
USER root
COPY ./emba/ /var/www/emba/

# * create user and add to sudoers [root]
USER root
RUN useradd www-embark -G sudo -c "embark-server-user" -M -r --shell=/usr/sbin/nologin -d /app/ && \
    echo 'www-embark ALL=(ALL) NOPASSWD: /app/emba/emba.sh' | EDITOR='tee -a' visudo

# * mkdir for apache
USER www-embark
RUN mkdir /var/www/media
RUN mkdir /var/www/media/uploadedFirmwareImages
RUN mkdir /app/media/emba_logs
RUN mkdir /app/static
RUN mkdir /app/conf

# * copy pipfile(s) and install pipenv [www-embark]
USER root
COPY --chown=www-embark:sudo ./Pipfile.lock /var/www/Pipfile.lock

USER www-embark
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install

# * copy embark [www-embark]
USER root
COPY --chown=www-embark:sudo ./embark /var/www/embark

# * write .env[-]

# * copy entrypoint.sh [root]
USER root
COPY ./entrypoint.sh /var/www/entrypoint.sh

WORKDIR /var/www/

EXPOSE 80
# Opening on extra port for our ASGI setup
EXPOSE 8001

# source start-script
ENTRYPOINT  ["./entrypoint.sh"]

