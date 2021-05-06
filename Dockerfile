FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \ 
    apt-get -y upgrade && \
    apt-get -y install wget kmod procps sudo && \
    sudo apt-get install -y apt-utils && \
    sudo apt-get install -y default-libmysqlclient-dev && \
    sudo apt-get install -y mysql-client && \
    sudo apt-get install -y python3-mysqldb && \
    sudo apt-get install -y build-essential && \
    sudo apt-get install -y python3-dev && \
    sudo apt-get install -y libssl-dev && \
    sudo apt-get install -y swig


ADD . /app

WORKDIR /app/embark


ADD embark/requirements.txt /app/embark/requirements.txt

RUN yes | sudo /app/emba/installer.sh -D -F  && \
    sudo pip3 install uwsgi -I --no-cache-dir && \
    pip3 install --user --no-warn-script-location -r /app/embark/requirements.txt && \
    mkdir /app/embark/logs


EXPOSE 8000
# Opening on extra port for our ASGI setup
EXPOSE 8001

CMD  ./entrypoint.sh
