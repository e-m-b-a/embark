FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive
ENV DJANGO_SETTINGS_MODULE=embark.settings
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.local/bin

RUN apt-get update && \ 
    apt-get -y upgrade && \
    apt-get -y install wget kmod procps sudo && \
    sudo apt-get install -y apt-utils && \
    sudo apt-get install -y default-libmysqlclient-dev && \
    sudo apt-get install -y default-mysql-client && \
    sudo apt-get install -y build-essential && \
    sudo apt-get install -y python3-dev && \
    sudo apt-get install -y libssl-dev && \
    sudo apt-get install -y swig

ADD . /app

WORKDIR /app/embark


ADD embark/requirements.txt /app/embark/requirements.txt

RUN yes | sudo /app/emba/installer.sh -D -F  && \
    sudo pip3 install uwsgi -I --no-cache-dir && \
    pip3 install --user --no-warn-script-location -r /app/embark/requirements.txt

# 8000 for http workers. 8001 for ws workers
EXPOSE 8000
# Opening on extra port for our ASGI setup
EXPOSE 8001

CMD  ./entrypoint.sh

