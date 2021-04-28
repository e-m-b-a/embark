FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \ 
    apt-get -y upgrade && \
    apt-get -y install wget kmod procps sudo

WORKDIR /app
ADD . /app

ADD embark/requirements.txt /app/embark/requirements.txt


RUN yes | sudo ./emba/installer.sh -D -F  && \
    sudo pip3 install uwsgi -I --no-cache-dir && \
    pip3 install --user --no-warn-script-location -r /app/embark/requirements.txt && \
    mkdir /app/embark/logs

EXPOSE 8000

CMD  ./embark/entrypoint.sh
