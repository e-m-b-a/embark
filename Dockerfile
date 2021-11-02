FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive
ENV DJANGO_SETTINGS_MODULE=embark.settings
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.local/bin

# TODO: clean. why pylint ?
RUN apt-get update && \ 
    apt-get -y upgrade && \
    apt-get -y -q install wget kmod procps sudo && \
    sudo apt-get install -y -q apt-utils && \
    sudo apt-get install -y -q default-libmysqlclient-dev && \
    sudo apt-get install -y -q default-mysql-client && \
    sudo apt-get install -y -q build-essential && \
    sudo apt-get install -y -q python3-dev && \
    sudo apt-get install -y -q libssl-dev && \
    sudo apt-get install -y -q python3-pylint-django && \
    sudo apt-get install -y -q pycodestyle && \
    sudo apt-get install -y -q swig

ADD . /app

WORKDIR /app/embark

ADD embark/requirements.txt /app/embark/requirements.txt

RUN yes | sudo /app/emba/installer.sh -D  && \
    sudo pip3 install uwsgi -I --no-cache-dir && \
    pip3 install --user --no-warn-script-location -r /app/embark/requirements.txt

# TODO dont expose 8001 to outside !!
# 80 for http workers. 8001 for ws workers
EXPOSE 80
# Opening on extra port for our ASGI setup
EXPOSE 8001

CMD  ./entrypoint.sh

