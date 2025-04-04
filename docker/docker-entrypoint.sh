#!/bin/bash

conf="/etc/patchman/local_settings.py"

# Configure ADMINS
if [ -n "${ADMIN_NAME}" ]; then
    sed -i '6 {s/Your Name/'"${ADMIN_NAME}"'/}' "$conf"
fi

if [ -n "${ADMIN_EMAIL}" ]; then
    sed -i '6 {s/you@example.com/'"${ADMIN_EMAIL}"'/}' "$conf"
fi

# Configure DATABASES
if [ -n "${DB_ENGINE}" ]; then
    sed -i '9,14 {/^#/ ! s/\(.*\)/#\1/}' "$conf"

    if [[ $(grep -c "ENGINE" "$conf") -lt 2 ]]; then
        if [ "${DB_ENGINE}" == "MySQL" ]; then
            if [ -n "${DB_PORT}" ]; then
                dbPort="${DB_PORT}"
            else
                dbPort="3306"
            fi

            cat <<-EOF >> "$conf"

			DATABASES = {
			    'default': {
			        'ENGINE': 'django.db.backends.mysql',
			        'NAME': '${DB_DATABASE}',
			        'USER': '${DB_USER}',
			        'PASSWORD': '${DB_PASSWORD}',
			        'HOST': '${DB_HOST}',
			        'PORT': '"$dbPort"',
			        'STORAGE_ENGINE': 'INNODB',
			        'CHARSET' : 'utf8'
			    }
			}
			EOF

        elif [ "${DB_ENGINE}" == "PostgreSQL" ]; then
            if [ -n "${DB_PORT}" ]; then
                dbPort="${DB_PORT}"
            else
                dbPort="5432"
            fi

            cat <<-EOF >> "$conf"

			DATABASES = {
			    'default': {
			        'ENGINE': 'django.db.backends.postgresql_psycopg2',
			        'NAME': '${DB_DATABASE}',
			        'USER': '${DB_USER}',
			        'PASSWORD': '${DB_PASSWORD}',
			        'HOST': '${DB_HOST}',
			        'PORT': '${DB_PORT}',
			        'CHARSET' : 'utf8'
			    }
			}
			EOF
        fi
    fi
fi

# Configure TIME_ZONE
if [ -n  "${TIMEZONE}" ]; then
    sed -i '18 {s/America\/New_York/'"${TIMEZONE/\//\\/}"'/}' "$conf"
fi

# Configure SECRET_KEY 
if [ -z "$(grep "SECRET_KEY" "$conf" | cut -d " " -f 3 | tr -d "'")" ]; then 
    if [ -n "${SECRET_KEY}" ]; then
        sed -i "s/SECRET_KEY = ''/SECRET_KEY = '"${SECRET_KEY}"'/g" "$conf" 
    else
        patchman-set-secret-key
    fi
fi

# Configure CACHES
if [ -n "${MEMCACHED_ADDR}" ]; then
    memcachedAddr="${MEMCACHED_ADDR}"

    if [ -n "${MEMCACHED_PORT}" ]; then
        memcachedPort="${MEMCACHED_PORT}"
    else
        memcachedPort="11211"
    fi

    sed -i "s/'LOCATION': '127.0.0.1:11211'/'LOCATION': '"$memcachedAddr":"$memcachedPort"'/g" "$conf" 
else
    sed -i '41,49 {/^#/ ! s/\(.*\)/#\1/}' "$conf"
fi

# Sync database on container first start
if [ ! -f /var/lib/patchman/.firstrun ]; then
    patchman-manage makemigrations
    patchman-manage migrate --run-syncdb --fake-initial
    patchman-manage collectstatic

    # If SQLite is being used, allow httpd to write
    if [ -z "${DB_ENGINE}" ]; then
        chmod 660 /var/lib/patchman/db/patchman.db
    fi

    touch /var/lib/patchman/.firstrun
fi

# Starts Celery for for realtime processing of reports from clients
if [ -n "${CELERY_BROKER}" ]; then
    broker="${CELERY_BROKER}"

    if [ -n "${CELERY_BROKER_PORT}" ]; then
        brokerPort="${CELERY_BROKER_PORT}"
    else
        brokerPort=6379
    fi

    if [ -z "$(grep "USE_ASYNC_PROCESSING" "$conf" | cut -d " " -f 3 | tr -d "'")" ]; then 
        echo "" >> "$conf"
        echo "USE_ASYNC_PROCESSING = True" >> "$conf"
    fi

    if [ -z "$(grep "CELERY_BROKER_URL" "$conf" | cut -d " " -f 3 | tr -d "'")" ]; then 
        echo "CELERY_BROKER_URL = 'redis://"$broker":"$brokerPort"/0'" >> "$conf"
    fi

    C_FORCE_ROOT=1 celery -b redis://"$broker":"$brokerPort"/0 -A patchman worker -l INFO -E &
fi

# Starts Apache httpd process
/usr/sbin/apache2ctl -DFOREGROUND

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
