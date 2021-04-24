FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \ 
    apt-get -y upgrade && \
    apt-get -y install wget kmod procps sudo

WORKDIR /app
ADD . /app

ADD embark/requirements.txt /app/embark/requirements.txt


RUN yes | sudo ./installer.sh -D -F  && \
    sudo pip3 install uwsgi -I --no-cache-dir && \
    pip3 install --user --no-warn-script-location -r /app/embark/requirements.txt && \
    mkdir /app/embark/logs

EXPOSE 8000


ENTRYPOINT [ "/bin/bash" ]
CMD uwsgi --wsgi-file /app/embark/embark/wsgi.py  --http :8001 --workers=2 ---master --threads=5 --enable-threads --lazy-apps --py-autoreload 10 --harakiri=60 --single-interpreter --reload-mercy=120 --worker-reload-mercy=120 --thunder-lock --max-requests=1000 --vacuum --ignore-sigpipe --ignore-write-errors --disable-write-exception --buffer-size 10000


