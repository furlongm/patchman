FROM ubuntu:18.04

# Set DEBIAN_FRONTEND env variable to suppress prompt for tzdata package install
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends gnupg2 ca-certificates \
    && apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0412F522 \
    && echo "deb https://repo.openbytes.ie/ubuntu bionic main" > /etc/apt/sources.list.d/patchman.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python-mysqldb \
        python-pymysql \
        mysql-client-5.7 \
        python-magic \
        cron \
    && apt-get install -y --no-install-recommends \
        python-patchman \
        patchman-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY files/patchman-cron-daily /etc/cron.d/patchman-cron-daily
RUN chmod 0644 /etc/cron.d/patchman-cron-daily \
    && crontab /etc/cron.d/patchman-cron-daily \
    && touch /var/log/patchman.log

EXPOSE 80
