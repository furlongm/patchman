#!/bin/bash
set -euo pipefail

log()  { echo "[INFO]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"; }
warn() { echo "[WARN]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }
die()  { echo "[ERROR] $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; exit 1; }

conf="/etc/patchman/local_settings.py"
[ -f "$conf" ] || die "Configuration file not found: $conf."

# Configure DEBUG
if [ "${DEBUG:-false}" = true ]; then
    log "DEBUG mode enabled."
    sed -i '3 {s/False/True/}' "$conf"
fi

# Configure ADMINS
if [ -n "${ADMIN_NAME:-}" ]; then
    sed -i '6 {s/Your Name/'"${ADMIN_NAME}"'/}' "$conf"
fi

if [ -n "${ADMIN_EMAIL:-}" ]; then
    sed -i '6 {s/you@example.com/'"${ADMIN_EMAIL}"'/}' "$conf"
fi

# Configure DATABASES
if [ -n "${DB_ENGINE:-}" ]; then
    sed -i '9,18 {/^#/ ! s/\(.*\)/#\1/}' "$conf"

    if [[ $(grep -v "#" "$conf" | grep -c "ENGINE") -lt 2 ]]; then
        case "${DB_ENGINE}" in
            SQLite)
            log "Using SQLite database."
            ;;
            MySQL)
                dbPort="${DB_PORT:-3306}"
                [ -n "${DB_DATABASE:-}" ] || die "DB_DATABASE is required for MySQL."
                [ -n "${DB_USER:-}" ]     || die "DB_USER is required for MySQL."
                [ -n "${DB_HOST:-}" ]     || die "DB_HOST is required for MySQL."
                log "Configuring MySQL database at ${DB_HOST}:${dbPort}."

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
            ;;

            PostgreSQL)
                dbPort="${DB_PORT:-5432}"
                [ -n "${DB_DATABASE:-}" ] || die "DB_DATABASE is required for PostgreSQL."
                [ -n "${DB_USER:-}" ]     || die "DB_USER is required for PostgreSQL."
                [ -n "${DB_HOST:-}" ]     || die "DB_HOST is required for PostgreSQL."
                log "Configuring PostgreSQL database at ${DB_HOST}:${dbPort}."

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
            ;;

            *)
                die "Invalid DB_ENGINE: '${DB_ENGINE}'." 
                ;;
        esac
    fi
fi

# Configure TIME_ZONE
if [ -n "${TIMEZONE:-}" ]; then
    sed -i '22 {s/America\/New_York/'"${TIMEZONE/\//\\/}"'/}' "$conf"
fi

# Configure LANGUAGE_CODE
if [ -n "${LANGUAGE_CODE:-}" ]; then
    sed -i '26 {s/en-us/'"${LANGUAGE_CODE}"'/}' "$conf"
fi

# Configure SECRET_KEY 
if [ -z "$(grep "SECRET_KEY" "$conf" | cut -d " " -f 3 | tr -d "'")" ]; then 
    if [ -n "${SECRET_KEY:-}" ]; then
        sed -i "29 {s/SECRET_KEY = ''/SECRET_KEY = '${SECRET_KEY}'/}" "$conf" 
    else
        patchman-set-secret-key
    fi
fi

# Configure MAX_MIRRORS
if [ -n "${MAX_MIRRORS:-}" ]; then
    sed -i '36 {s/2/'"${MAX_MIRRORS}"'/}' "$conf"
fi

# Configure MAX_MIRROR_FAILURES
if [ -n "${MAX_MIRROR_FAILURES:-}" ]; then
    sed -i '39 {s/14/'"${MAX_MIRROR_FAILURES}"'/}' "$conf"
fi

# Configure DAYS_WITHOUT_REPORT
if [ -n "${DAYS_WITHOUT_REPORT:-}" ]; then
    sed -i '42 {s/14/'"${DAYS_WITHOUT_REPORT}"'/}' "$conf"
fi

# Configure ERRATA_OS_UPDATES
if [ -n "${ERRATA_OS_UPDATES:-}" ]; then
    errataOSUpdates="${ERRATA_OS_UPDATES// /}"
    sed -i '45 {s/\[.*\]/['"'${errataOSUpdates//,/\', \'}'"']/}' "$conf"
fi

# Configure ALMA_RELEASES
if [ -n "${ALMA_RELEASES:-}" ]; then
    sed -i '48 {s/\[.*\]/['"${ALMA_RELEASES}"']/}' "$conf"
fi

# Configure DEBIAN_CODENAMES
if [ -n "${DEBIAN_CODENAMES:-}" ]; then
    debianCodenames="${DEBIAN_CODENAMES// /}"
    sed -i '51 {s/\[.*\]/['"'${debianCodenames//,/\', \'}'"']/}' "$conf"
fi

# Configure UBUNTU_CODENAMES
if [ -n "${UBUNTU_CODENAMES:-}" ]; then
    ubuntuCodenames="${UBUNTU_CODENAMES// /}"
    sed -i '54 {s/\[.*\]/['"'${ubuntuCodenames//,/\', \'}'"']/}' "$conf"
fi

# Configure CACHES
redisHost="${REDIS_HOST:-127.0.0.1}"
redisPort="${REDIS_PORT:-6379}"

if [ "${USE_CACHE:-false}" = true ]; then
    log "Configuring Redis cache at ${redisHost}:${redisPort}."
    sed -i "62 {s/127.0.0.1:6379/$redisHost:$redisPort/}" "$conf"

    if [ -n "${CACHE_TIMEOUT:-}" ]; then
        sed -i "67 {s/0/${CACHE_TIMEOUT}/}" "$conf"
    fi
else
    log "Cache disabled, using DummyCache."
    sed -i '61 {s/redis.RedisCache/dummy.DummyCache/}' "$conf"
    sed -i '62 {/^#/ ! s/\(.*\)/#\1/}' "$conf"
fi

# Sync database on container first start
if [ ! -f /var/lib/patchman/.firstrun ]; then
    log "First run detected, initialising database..."
    log "Running makemigrations..."
    patchman-manage makemigrations
    log "Running migrate..."
    patchman-manage migrate --run-syncdb --fake-initial
    log "Running collectstatic..."
    patchman-manage collectstatic --noinput

    if [ -z "${DB_ENGINE:-}" ]; then
        chmod 660 /var/lib/patchman/db/patchman.db
    fi

    touch /var/lib/patchman/.firstrun
    log "Initialisation complete."
fi

if [ "${USE_CELERY:-false}" = true ]; then
    log "Starting Celery worker..."

    if [ -z "$(grep "USE_ASYNC_PROCESSING" "$conf" | cut -d " " -f 3 | tr -d "'")" ]; then 
        echo "" >> "$conf"
        echo "USE_ASYNC_PROCESSING = True" >> "$conf"
    fi

    if [ -z "$(grep "CELERY_BROKER_URL" "$conf" | cut -d " " -f 3 | tr -d "'")" ]; then 
        echo "CELERY_BROKER_URL = 'redis://$redisHost:$redisPort/0'" >> "$conf"
    fi

    gosu www-data celery \
        -b redis://"$redisHost":"$redisPort"/0 \
        -A patchman worker \
        -l INFO -E &
fi

# Starts Apache httpd process
log "Starting Apache..."
exec /usr/sbin/apache2ctl -DFOREGROUND
