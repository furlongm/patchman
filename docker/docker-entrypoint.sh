#!/bin/bash

# Configure ADMINS
if [ ! -z "${ADMIN_NAME}" ]; then
    sed -i '6 {s/Your Name/'"${ADMIN_NAME}"'/}' /etc/patchman/local_settings.py
fi

if [ ! -z "${ADMIN_EMAIL}" ]; then
    sed -i '6 {s/you@example.com/'"${ADMIN_EMAIL}"'/}' /etc/patchman/local_settings.py
fi

# Configure DATABASES
if [ ! -z "${DB_ENGINE}" ]; then
    sed -i '9,14 {/^#/ ! s/\(.*\)/#\1/}' /etc/patchman/local_settings.py

    if [[ $(grep "ENGINE" /etc/patchman/local_settings.py | wc -l) < 2 ]]; then
        if [ "${DB_ENGINE}" == "MySQL" ]; then
            if [ ! -z "${DB_PORT}" ]; then
                dbPort="${DB_PORT}"
            else
                dbPort="3306"
            fi

            cat <<-EOF >> /etc/patchman/local_settings.py

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
            if [ ! -z "${DB_PORT}" ]; then
                dbPort="${DB_PORT}"
            else
                dbPort="5432"
            fi

            cat <<-EOF >> /etc/patchman/local_settings.py

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
if [ ! -z "${TIMEZONE}" ]; then
    sed -i '18 {s/America\/New_York/'"${TIMEZONE/\//\\/}"'/}' /etc/patchman/local_settings.py
fi

# Configure SECRET_KEY 
if [ -z $(grep "SECRET_KEY" /etc/patchman/local_settings.py | cut -d " " -f 3 | tr -d "'") ]; then 
    if [ ! -z "${SECRET_KEY}" ]; then
        sed -i "s/SECRET_KEY = ''/SECRET_KEY = '"${SECRET_KEY}"'/g" /etc/patchman/local_settings.py 
    else
        patchman-set-secret-key
    fi
fi

# Configure CACHES
if [ ! -z "${MEMCACHED_ADDR}" ]; then
    memcachedAddr="${MEMCACHED_ADDR}"

    if [ ! -z "${MEMCACHED_PORT}" ]; then
        memcachedPort="${MEMCACHED_PORT}"
    else
        memcachedPort="11211"
    fi

    sed -i "s/'LOCATION': '127.0.0.1:11211'/'LOCATION': '"$memcachedAddr":"$memcachedPort"'/g" /etc/patchman/local_settings.py 
else
    sed -i '41,49 {/^#/ ! s/\(.*\)/#\1/}' /etc/patchman/local_settings.py
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
if [ ! -z "${CELERY_BROKER}" ]; then
    broker="${CELERY_BROKER}"

    if [ ! -z "${CELERY_BROKER_PORT}" ]; then
        brokerPort="${CELERY_BROKER_PORT}"
    else
        brokerPort=6379
    fi

    if [ -z $(grep "USE_ASYNC_PROCESSING" /etc/patchman/local_settings.py | cut -d " " -f 3 | tr -d "'") ]; then 
        echo "" >> /etc/patchman/local_settings.py
        echo "USE_ASYNC_PROCESSING = True" >> /etc/patchman/local_settings.py
    fi

    if [ -z $(grep "CELERY_BROKER_URL" /etc/patchman/local_settings.py | cut -d " " -f 3 | tr -d "'") ]; then 
        echo "CELERY_BROKER_URL = 'redis://"$broker":"$brokerPort"/0'" >> /etc/patchman/local_settings.py
    fi

    C_FORCE_ROOT=1 celery -b redis://"$broker":"$brokerPort"/0 -A patchman worker -l INFO -E &
fi

# Starts Apache httpd process
/usr/sbin/apache2ctl -DFOREGROUND

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
