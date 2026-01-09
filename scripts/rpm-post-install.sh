#!/bin/sh

if [ ! -e /etc/httpd/conf.d/patchman.conf ] ; then
    cp /etc/patchman/apache.conf.example /etc/httpd/conf.d/patchman.conf
fi

PYTHON_SITEPACKAGES=$(python3 -c "import site; print(site.getsitepackages()[0])")
if ! grep "${PYTHON_SITEPACKAGES}" /etc/httpd/conf.d/patchman.conf >/dev/null 2>&1 ; then
    sed -i -e "s|^\(Define patchman_pythonpath\).*|\1 ${PYTHON_SITEPACKAGES}|" \
    /etc/httpd/conf.d/patchman.conf
fi

systemctl enable httpd
systemctl restart httpd
systemctl enable redis
systemctl start redis

patchman-set-secret-key
chown apache /etc/patchman/local_settings.py

mkdir -p /var/lib/patchman/db
patchman-manage collectstatic --noinput

patchman-manage makemigrations
patchman-manage migrate --run-syncdb --fake-initial
sqlite3 /var/lib/patchman/db/patchman.db 'PRAGMA journal_mode=WAL;'

adduser --system --shell /sbin/nologin patchman
usermod -a -G patchman apache
chown root:patchman /etc/patchman/celery.conf
chmod 640 /etc/patchman/celery.conf
chown -R patchman:patchman /var/lib/patchman
semanage fcontext -a -t httpd_sys_rw_content_t "/var/lib/patchman/db(/.*)?"
restorecon -Rv /var/lib/patchman/db
setsebool -P httpd_can_network_connect 1

WORKER_COUNT=1
if [ -f /etc/patchman/celery.conf ]; then
    . /etc/patchman/celery.conf
    WORKER_COUNT=${CELERY_WORKER_COUNT:-1}
fi

for i in $(seq 1 "${WORKER_COUNT}"); do
    systemctl enable --now "patchman-celery-worker@$i.service"
done

active_instances=$(systemctl list-units --type=service --state=active "patchman-celery-worker@*" --no-legend | awk '{print $1}')
for service in $active_instances; do
    inst_num=$(echo "$service" | cut -d'@' -f2 | cut -d'.' -f1)
    if [ "$inst_num" -gt "${WORKER_COUNT}" ]; then
        systemctl stop "$service"
        systemctl disable "$service"
    fi
done

systemctl enable --now patchman-celery-beat.service

echo
echo "Remember to run 'patchman-manage createsuperuser' to create a user."
echo
