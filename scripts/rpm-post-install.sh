#!/bin/sh

if [ ! -e /etc/httpd/conf.d/patchman.conf ] ; then
    cp /etc/patchman/apache.conf.example /etc/httpd/conf.d/patchman.conf
fi

if ! grep /usr/lib/python3.6/site-packages /etc/httpd/conf.d/patchman.conf >/dev/null 2>&1 ; then
    sed -i -e "s/^\(Define patchman_pythonpath\).*/\1 \/usr\/lib\/python3.6\/site-packages/" \
    /etc/httpd/conf.d/patchman.conf
fi

service httpd reload

patchman-set-secret-key
chown apache /etc/patchman/local_settings.py

mkdir -p /var/lib/patchman/db
patchman-manage collectstatic --noinput

patchman-manage makemigrations
patchman-manage migrate --run-syncdb

chown -R apache:apache /var/lib/patchman
chcon --type httpd_sys_rw_content_t /var/lib/patchman/db/patchman.db
semanage port -a -t http_port_t -p tcp 5672
setsebool -P httpd_can_network_memcache 1
setsebool -P httpd_can_network_connect 1

echo
echo "Remember to run 'patchman-manage createsuperuser' to create a user."
echo
