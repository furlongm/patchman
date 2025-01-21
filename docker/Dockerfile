FROM debian:bookworm-slim

RUN apt update && apt upgrade
RUN apt install -y apache2 libapache2-mod-wsgi-py3 mariadb-client python-celery-common python3-celery python3-colorama python3-debian python3-defusedxml python3-django python3-django-extensions python3-django-tagging python3-djangorestframework python3-humanize python3-lxml python3-magic python3-mysqldb python3-pip python3-progressbar python3-pymemcache python3-redis python3-requests python3-rpm sendmail sharutils uuid-runtime weasyprint

RUN pip3 install django-bootstrap3 --break-system-packages

RUN mkdir -p /srv/patchman && mkdir -p /var/lib/patchman/db

COPY . /srv/patchman/
COPY ./sbin/* /usr/bin/
COPY ./email/patchman-email /usr/bin/
COPY ./etc/patchman/local_settings.py /etc/patchman/
COPY ./etc/patchman/patchman-email.conf /etc/patchman/
COPY ./etc/patchman/apache.conf.example /etc/apache2/sites-available/patchman.conf

RUN a2enmod wsgi
RUN a2ensite patchman

RUN chown -R :www-data /etc/patchman && chmod -R g+r /etc/patchman
RUN chown -R :www-data /var/lib/patchman && chmod -R g+w /var/lib/patchman/db
RUN chmod +x /srv/patchman/patchman/*.py

EXPOSE 80

COPY ./docker/docker-entrypoint.sh docker-entrypoint.sh
ENTRYPOINT ./docker-entrypoint.sh
