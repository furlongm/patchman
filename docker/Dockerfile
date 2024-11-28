FROM debian:bookworm-slim

RUN apt update \
    && apt install -y curl mariadb-client python3-mysqldb python3-pymemcache python3-celery python3-redis python-celery-common

RUN curl -sS https://repo.openbytes.ie/openbytes.gpg > /usr/share/keyrings/openbytes.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/openbytes.gpg] https://repo.openbytes.ie/patchman/debian bookworm main" > /etc/apt/sources.list.d/patchman.list

RUN apt update \
    && apt install -y python3-patchman

EXPOSE 80

COPY ./docker-entrypoint.sh docker-entrypoint.sh
ENTRYPOINT ./docker-entrypoint.sh
