FROM debian:trixie-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATCHMAN_HOME=/srv/patchman

RUN apt-get -y update && apt-get -y upgrade && \
    apt-get install -y --no-install-recommends \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${PATCHMAN_HOME}

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages setuptools -r requirements.txt

COPY . ${PATCHMAN_HOME}/

RUN ${PATCHMAN_HOME}/setup.py install --no-compile && \
    rm -rf build/ dist/ *.egg-info/ .eggs/ /root/.cache/


FROM debian:trixie-slim AS runtime

LABEL maintainer="4950815+RicardoJeronimo@users.noreply.github.com" \
      org.opencontainers.image.title="Patchman" \
      org.opencontainers.image.base.name="debian:trixie-slim" \
      org.opencontainers.image.source="https://github.com/RicardoJeronimo/patchman"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATCHMAN_HOME=/srv/patchman

RUN apt-get -y update && apt-get -y upgrade && \
    apt-get install -y --no-install-recommends \
        apache2 \
        curl \
        git \
        gosu \
        libapache2-mod-wsgi-py3 \
        libmagic1 \
        mariadb-client \
        python3-debian \
        python3-defusedxml \
        python3-lxml \
        python3-mysqldb \
        python3-packaging \
        python3-psycopg2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${PATCHMAN_HOME}

COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/local/bin/patchman* /usr/local/bin/
COPY --from=builder /usr/local/bin/celery /usr/local/bin/
COPY --from=builder /etc/patchman/ /etc/patchman/
COPY --from=builder ${PATCHMAN_HOME}/ ${PATCHMAN_HOME}/

RUN cp ${PATCHMAN_HOME}/etc/patchman/apache.conf.example /etc/apache2/sites-available/patchman.conf && \
    echo "ServerName localhost" >> /etc/apache2/apache2.conf && \
    a2enmod wsgi && \
    a2ensite patchman && \
    a2dissite 000-default && \
    groupadd --system patchman && \
    useradd --system --gid patchman --no-create-home patchman && \
    mkdir -p /var/lib/patchman/db && \
    chown patchman:www-data /var/lib/patchman/db && \
    chmod 2770 /var/lib/patchman/db

COPY ./docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost/patchman/ || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
