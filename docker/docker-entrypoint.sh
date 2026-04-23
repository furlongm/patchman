#!/bin/bash

conf="/etc/patchman/local_settings.py"

# Configure DEBUG
if "${DEBUG}"; then
    sed -i '3 {s/False/True/}' "$conf"
fi

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
if [ -n "${TIMEZONE}" ]; then
    sed -i '22 {s/America\/New_York/'"${TIMEZONE/\//\\/}"'/}' "$conf"
fi

# Configure LANGUAGE_CODE
if [ -n "${LANGUAGE_CODE}" ]; then
    sed -i '26 {s/en-us/'"${LANGUAGE_CODE}"'/}' "$conf"
fi

# Configure SECRET_KEY 
if [ -z "$(grep "SECRET_KEY" "$conf" | cut -d " " -f 3 | tr -d "'")" ]; then 
    if [ -n "${SECRET_KEY}" ]; then
        sed -i "29 {s/SECRET_KEY = ''/SECRET_KEY = '${SECRET_KEY}'/}" "$conf" 
    else
        patchman-set-secret-key
    fi
fi

# Configure MAX_MIRRORS
if [ -n "${MAX_MIRRORS}" ]; then
    sed -i '36 {s/2/'"${MAX_MIRRORS}"'/}' "$conf"
fi

# Configure MAX_MIRROR_FAILURES
if [ -n "${MAX_MIRROR_FAILURES}" ]; then
    sed -i '39 {s/14/'"${MAX_MIRROR_FAILURES}"'/}' "$conf"
fi

# Configure DAYS_WITHOUT_REPORT
if [ -n "${DAYS_WITHOUT_REPORT}" ]; then
    sed -i '42 {s/14/'"${DAYS_WITHOUT_REPORT}"'/}' "$conf"
fi

# Configure ERRATA_OS_UPDATES
if [ -n "${ERRATA_OS_UPDATES}" ]; then
    errataOSUpdates="${ERRATA_OS_UPDATES// /}"
    sed -i '45 {s/\[.*\]/['"'${errataOSUpdates//,/\', \'}'"']/}' "$conf"
fi

# Configure ALMA_RELEASES
if [ -n "${ALMA_RELEASES}" ]; then
    sed -i '48 {s/\[.*\]/['"${ALMA_RELEASES}"']/}' "$conf"
fi

# Configure DEBIAN_CODENAMES
if [ -n "${DEBIAN_CODENAMES}" ]; then
    debianCodenames="${DEBIAN_CODENAMES// /}"
    sed -i '51 {s/\[.*\]/['"'${debianCodenames//,/\', \'}'"']/}' "$conf"
fi

# Configure UBUNTU_CODENAMES
if [ -n "${UBUNTU_CODENAMES}" ]; then
    ubuntuCodenames="${UBUNTU_CODENAMES// /}"
    sed -i '54 {s/\[.*\]/['"'${ubuntuCodenames//,/\', \'}'"']/}' "$conf"
fi

# Configure CACHES
if "${USE_CACHE}"; then
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

    # Change RedisCache LOCATION
    sed -i "62 {s/127.0.0.1:6379/$redisHost:$redisPort/}" "$conf"

    if [ -n "${CACHE_TIMEOUT}" ]; then
        sed -i "67 {s/0/${CACHE_TIMEOUT}/}" "$conf"
    fi
else
    # Change RedisCache to DummyCache to avoid ConnectionError and comment LOCATION
    sed -i '61 {s/redis.RedisCache/dummy.DummyCache/}' "$conf"
    sed -i '62 {/^#/ ! s/\(.*\)/#\1/}' "$conf"
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
if "${USE_CELERY}"; then
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
