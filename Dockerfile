FROM python:2

RUN apt-get update && apt-get install -y \
            git \
            libcap-dev \
            libjansson-dev \
            libpcre3-dev \
            librsvg2-bin \
            libsasl2-dev \
            libyaml-dev \
            optipng \
            uuid-dev

WORKDIR /usr/src/uwsgi

# prepare uwsgi
RUN wget -O uwsgi-2.0.14.tar.gz https://github.com/unbit/uwsgi/archive/2.0.14.tar.gz && \
        tar --strip-components=1 -axvf uwsgi-2.0.14.tar.gz
COPY uwsgi_profile.ini buildconf/wuvt.ini

# build and install uwsgi
RUN python uwsgiconfig.py --build wuvt && cp uwsgi /usr/local/bin/ && \
        mkdir -p /usr/local/lib/uwsgi/plugins

WORKDIR /usr/src/app

# install python dependencies
COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

# copy application
ADD migrations /usr/src/app/migrations
ADD wuvt /usr/src/app/wuvt
COPY LICENSE README.md uwsgi_docker.ini /usr/src/app/

VOLUME ["/data/config", "/data/media", "/data/ssl"]

EXPOSE 8443
ENV PYTHONPATH /usr/src/app
ENV FLASK_APP wuvt
ENV APP_CONFIG_PATH /data/config/config.py

RUN flask render_images

CMD ["uwsgi", "--ini", "uwsgi_docker.ini"]
