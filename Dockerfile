FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive
ENV DJANGO_SETTINGS_MODULE=embark.settings
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.local/bin

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
RUN sudo apt-get install -y -q python3-pip

ADD . /app

WORKDIR /app/embark

ADD embark/requirements.txt /app/embark/requirements.txt

RUN yes | sudo pip3 install uwsgi -I --no-cache-dir && \
    pip3 install --user --no-warn-script-location -r /app/embark/requirements.txt

RUN mkdir -p /app/embark/static/external/scripts && \
  mkdir -p /app/embark/static/external/css && \
  wget -O /app/embark/static/external/scripts/jquery.js https://code.jquery.com/jquery-3.6.0.min.js && \
  wget -O /app/embark/static/external/scripts/confirm.js https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.js && \
  wget -O /app/embark/static/external/scripts/bootstrap.js https://cdn.jsdelivr.net/npm/bootstrap@5.1.1/dist/js/bootstrap.bundle.min.js && \
  wget -O /app/embark/static/external/scripts/datatable.js https://cdn.datatables.net/v/bs5/dt-1.11.2/datatables.min.js && \
  wget -O /app/embark/static/external/scripts/charts.js https://cdn.jsdelivr.net/npm/chart.js@3.5.1/dist/chart.min.js && \
  wget -O /app/embark/static/external/css/confirm.css https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.css && \
  wget -O /app/embark/static/external/css/bootstrap.css https://cdn.jsdelivr.net/npm/bootstrap@5.1.1/dist/css/bootstrap.min.css && \
  wget -O /app/embark/static/external/css/datatable.css https://cdn.datatables.net/v/bs5/dt-1.11.2/datatables.min.css && \
  find /app/embark/static/external/ -type f -exec sed -i '/sourceMappingURL/d' {} \;


# 80 for http workers. 8001 for ws workers
EXPOSE 80
# Opening on extra port for our ASGI setup
EXPOSE 8001

CMD  ./entrypoint.sh

