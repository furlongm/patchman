#!/bin/bash

# Configure ADMINS
# To do

# Configure DATABASES
# To do

# Configure TIME_ZONE
# To do

# Configure SECRET_KEY if not set
if [ -z $(grep "SECRET_KEY" /etc/patchman/local_settings.py | cut -d " " -f 3 | tr -d "'") ]; then 
    if [ ! -z "${SECRET_KEY}" ]; then
        sed -i "s/SECRET_KEY = ''/SECRET_KEY = '"${SECRET_KEY}"'/g" /etc/patchman/local_settings.py 
    else
        patchman-set-secret-key
    fi
fi

# Configure CACHES
# To do

# Configure ASYNC_PROCESSING
# To do

# Starts Apache httpd process
/usr/sbin/apache2ctl -DFOREGROUND &

# Starts Celery for for realtime processing of reports from clients
if [ ! -z "${CELERY_BROKER}" ]; then
    broker="${CELERY_BROKER}"

    if [ ! -z "${CELERY_BROKER_PORT}" ]; then
        brokerPort="${CELERY_BROKER_PORT}"
    else
        brokerPort=6379
    fi

    C_FORCE_ROOT=1 celery -b redis://"$broker":"$brokerPort"/0 -A patchman worker -l INFO -E
fi

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
