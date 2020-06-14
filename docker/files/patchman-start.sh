#!/bin/bash

set -e
DB_HOST=database

while ! mysqladmin ping -h"$DB_HOST" --silent; do
    echo "Waiting for database connection..."
    sleep 5
done
cron -f &
patchman-manage makemigrations
patchman-manage migrate --run-syncdb
patchman-manage collectstatic --noinput
/usr/sbin/apache2ctl -DFOREGROUND
