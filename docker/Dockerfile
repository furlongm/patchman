FROM debian:bookworm-slim

RUN apt -y update && apt -y upgrade
RUN apt install -y apache2 libapache2-mod-wsgi-py3 mariadb-client python-celery-common python3-celery python3-debian python3-defusedxml python3-lxml python3-mysqldb python3-pip python3-progressbar python3-psycopg2 python3-redis python3-rpm sendmail sharutils uuid-runtime weasyprint

WORKDIR /srv/patchman

COPY . /srv/patchman/
COPY ./etc/patchman/apache.conf.example /etc/apache2/sites-available/patchman.conf

RUN /srv/patchman/setup.py install

COPY ./etc/patchman/patchman-email.conf /etc/patchman/
COPY ./email/patchman-email /usr/bin/patchman-email

RUN a2enmod wsgi
RUN a2ensite patchman

RUN mkdir -p /var/lib/patchman/db
RUN chown :www-data /var/lib/patchman/db && chmod 2770 /var/lib/patchman/db

EXPOSE 80

COPY ./docker/docker-entrypoint.sh docker-entrypoint.sh
ENTRYPOINT ["./docker-entrypoint.sh"]
