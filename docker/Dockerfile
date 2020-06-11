FROM ubuntu:18.04

# Set DEBIAN_FRONTEND env variable to suppress prompt for tzdata package install
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y gnupg2 ca-certificates \
    && apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0412F522 \
    && echo "deb https://repo.openbytes.ie/ubuntu bionic main" > /etc/apt/sources.list.d/patchman.list \
    && apt-get update \
    && apt-get -y install \
        python-mysqldb \
        python-pymysql \
        mysql-client-5.7 \
    && apt-get -y install \
        python-patchman \
        patchman-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 80
