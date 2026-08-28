#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until python -c "
import psycopg2, os, sys
try:
    psycopg2.connect(
        host=os.environ['DB_HOST'],
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
    )
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    echo "PostgreSQL unavailable - retrying in 2s..."
    sleep 2
done
echo "PostgreSQL is ready."

# Wait for Redis to be ready
echo "Waiting for Redis..."
until python -c "
import redis, os, sys
try:
    r = redis.Redis(host=os.environ.get('REDIS_HOST', 'redis'), port=int(os.environ.get('REDIS_PORT', 6379)))
    r.ping()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    echo "Redis unavailable - retrying in 2s..."
    sleep 2
done
echo "Redis is ready."

CMD="${1:-web}"

if [ "$CMD" = "web" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput

    echo "Collecting static files..."
    python manage.py collectstatic --noinput

    echo "Starting Gunicorn..."
    exec gunicorn patchman.wsgi \
        --bind 0.0.0.0:8000 \
        --workers "${GUNICORN_WORKERS:-4}" \
        --threads "${GUNICORN_THREADS:-2}" \
        --timeout "${GUNICORN_TIMEOUT:-120}" \
        --access-logfile - \
        --error-logfile -

elif [ "$CMD" = "celery-worker" ]; then
    echo "Starting Celery worker..."
    exec celery \
        --app patchman \
        worker \
        --loglevel "${CELERY_LOG_LEVEL:-info}" \
        --pool "${CELERY_POOL_TYPE:-threads}" \
        --concurrency "${CELERY_CONCURRENCY:-4}" \
        --task-events \
        --hostname "patchman-worker@%h"

elif [ "$CMD" = "celery-beat" ]; then
    echo "Starting Celery beat..."
    exec celery \
        --app patchman \
        beat \
        --loglevel "${CELERY_LOG_LEVEL:-info}" \
        --scheduler django_celery_beat.schedulers:DatabaseScheduler

else
    exec "$@"
fi
