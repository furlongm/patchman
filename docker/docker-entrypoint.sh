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
    sed -i '9,18 {/^#/ ! s/\(.*\)/#\1/}' "$conf"

    if [[ $(grep -v "#" "$conf" | grep -c "ENGINE") -lt 2 ]]; then
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
			        'PORT': '$dbPort',
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
			        'PORT': '$dbPort',
			        'CHARSET' : 'utf8'
			    }
			}
			EOF
        fi
    fi
fi

# Configure TIME_ZONE
if [ -n  "${TIMEZONE}" ]; then
    sed -i '22 {s/America\/New_York/'"${TIMEZONE/\//\\/}"'/}' "$conf"
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
if [ "${USE_CACHE}" ]; then
    if [ -n "${REDIS_HOST}" ]; then
        redisHost="${REDIS_HOST}"
    else
        redisHost="127.0.0.1"
    fi

    if [ -n "${REDIS_PORT}" ]; then
        redisPort="${REDIS_PORT}"
    else
        redisPort="6379"
    fi

    # Comment DummyCache Block
    sed -i '47,51 {/^#/ ! s/\(.*\)/#\1/}' "$conf"

    # Uncomment RedisCache Block
    sed -i '55,61 {s/^# //}' "$conf"

    sed -i "58 {s/127.0.0.1:6379/$redisHost:$redisPort/}" "$conf" 

    if [ -n "${CACHE_TIMEOUT}" ]; then
        sed -i "59 {s/30/${CACHE_TIMEOUT}/}" "$conf" 
    fi
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
if [ "${USE_CELERY}" ]; then
    if [ -n "${REDIS_HOST}" ]; then
        redisHost="${REDIS_HOST}"
    else
        redisHost="127.0.0.1"
    fi

    if [ -n "${REDIS_PORT}" ]; then
        redisPort="${REDIS_PORT}"
    else
        redisPort=6379
    fi

    if [ -z "$(grep "USE_ASYNC_PROCESSING" "$conf" | cut -d " " -f 3 | tr -d "'")" ]; then 
        echo "" >> "$conf"
        echo "USE_ASYNC_PROCESSING = True" >> "$conf"
    fi

    if [ -z "$(grep "CELERY_BROKER_URL" "$conf" | cut -d " " -f 3 | tr -d "'")" ]; then 
        echo "CELERY_BROKER_URL = 'redis://$redisHost:$redisPort/0'" >> "$conf"
    fi

    C_FORCE_ROOT=1 celery -b redis://"$redisHost":"$redisPort"/0 -A patchman worker -l INFO -E &
fi

# Starts Apache httpd process
/usr/sbin/apache2ctl -DFOREGROUND

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
