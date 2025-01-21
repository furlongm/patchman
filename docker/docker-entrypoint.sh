#!/bin/bash

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
