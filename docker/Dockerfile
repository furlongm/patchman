FROM debian:bookworm-slim

RUN apt update \
    && apt install -y curl mariadb-client python-celery-common python3-celery python3-mysqldb python3-pymemcache python3-redis sendmail sharutils uuid-runtime weasyprint

RUN curl -sS https://repo.openbytes.ie/openbytes.gpg > /usr/share/keyrings/openbytes.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/openbytes.gpg] https://repo.openbytes.ie/patchman/debian bookworm main" > /etc/apt/sources.list.d/patchman.list

RUN apt update \
    && apt install -y python3-patchman

RUN curl -sS https://raw.githubusercontent.com/RicardoJeronimo/patchman/master/email/patchman-email > /usr/bin/patchman-email \
    && curl -sS https://raw.githubusercontent.com/RicardoJeronimo/patchman/master/etc/patchman/patchman-email.conf > /etc/patchman/patchman-email.conf
RUN chmod +x /usr/bin/patchman-email

EXPOSE 80

COPY ./docker-entrypoint.sh docker-entrypoint.sh
ENTRYPOINT ./docker-entrypoint.sh
