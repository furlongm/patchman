#!/bin/sh

# Starts Apache httpd process
/usr/sbin/apache2ctl -DFOREGROUND &

# Starts Celery for for realtime processing of reports from clients
C_FORCE_ROOT=1 celery -b redis://redis:6379/0 -A patchman worker -l INFO -E

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
