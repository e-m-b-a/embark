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

RUN mkdir /app
# * use emba from host or copy [root]
USER root
COPY ./emba/ /var/www/emba/

# * create user and add to sudoers [root]
USER root
RUN useradd www-embark -G sudo -c "embark-server-user" -M -r --shell=/usr/sbin/nologin -d /app/ && \
    echo 'www-embark ALL=(ALL) NOPASSWD: /app/emba/emba.sh' | EDITOR='tee -a' visudo

# * mkdir for apache
USER www-embark
RUN mkdir /app/media && mkdir /app/media/uploadedFirmwareImages && mkdir /app/media/emba_logs && \
    mkdir /app/static && mkdir /app/conf

# * copy pipfile(s) and install pipenv [www-embark]
USER root
COPY --chown=www-embark:sudo ./Pipfile.lock /var/www/Pipfile.lock

USER www-embark
COPY ./Pipfile.lock /app/Pipfile.lock
RUN pipenv install

# * copy embark [www-embark]
USER www-embark
COPY ./embark /app/embark

# * copy .env[-]
COPY ./.env /app/.env
WORKDIR /app/

EXPOSE 80
# Opening on extra port for our ASGI setup
EXPOSE 8001

# source start-script TODO basically run-server.sh
ENTRYPOINT  ["./entrypoint.sh"]

