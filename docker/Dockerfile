FROM python:2.7-alpine

ARG BRANCH=master
ARG DEBIAN_FRONTEND=noninteractive

RUN apk --no-cache add --update \
        libmagic \
        libxslt-dev \
        postgresql-dev && \
    apk --no-cache add --virtual .build-deps --update \
        git \
        gcc \
        musl-dev && \
    git init /srv/patchman && \
    (cd /srv/patchman && \
        git fetch --tags https://github.com/furlongm/patchman.git $BRANCH && \
        git checkout FETCH_HEAD) && \
    pip install --no-cache-dir \
        -r /srv/patchman/requirements.txt \
        django-environ \
        psycopg2 \
        gunicorn \
        whitenoise==3.3.1 && \
    apk del .build-deps

COPY ./local_settings.py /usr/local/etc/patchman/
WORKDIR /srv/patchman

ENV PYTHONPATH /srv/patchman

EXPOSE 8000

CMD ["gunicorn", "--bind", ":8000", "--workers", "3", "patchman.wsgi:application"]
