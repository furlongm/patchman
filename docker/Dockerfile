FROM ubuntu:18.04

# Set DEBIAN_FRONTEND env variable to suppress prompt for tzdata package install
ENV DEBIAN_FRONTEND=noninteractive
ENV ADMIN_EMAIL=admin@example.com

RUN apt-get update && \
    apt-get install -y gnupg2 ca-certificates && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0412F522 && \
    echo "deb https://repo.openbytes.ie/ubuntu bionic main" > /etc/apt/sources.list.d/patchman.list && \
    apt-get update && \
    apt-get -y install \
        python-mysqldb \
        python-pymysql && \
    apt-get -y install \
        python-patchman \
        patchman-client && \
    patchman-manage createsuperuser --username admin --email ${ADMIN_EMAIL} --noinput

ENTRYPOINT ["/bin/bash"]
