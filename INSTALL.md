# Installation

The default installation uses sqlite3 for the django database. To configure
mysql or postgresql instead, see the database configuration section.


## Supported Install Options
  - [Ubuntu 18.04](#ubuntu-1804-bionic)
  - [Debian 10](#debian-10-buster)
  - [CentOS 7](#centos-7)
  - [virtualenv + pip](#virtualenv--pip)
  - [Source](#source)


### Ubuntu 18.04 (bionic)

```shell
apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0412F522
echo "deb https://repo.openbytes.ie/ubuntu bionic main" > /etc/apt/sources.list.d/patchman.list
apt update
apt -y install python-patchman patchman-client
patchman-manage createsuperuser
```

### Debian 10 (buster)

```shell
apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0412F522
echo "deb https://repo.openbytes.ie/debian buster main" > /etc/apt/sources.list.d/patchman.list
apt update
apt -y install python-patchman patchman-client
patchman-manage createsuperuser
```

### CentOS 7

```shell
cat <<EOF >> /etc/yum.repos.d/openbytes.repo
[openbytes]
name=openbytes
baseurl=https://repo.openbytes.ie/yum
enabled=1
gpgcheck=0
EOF
yum install -y epel-release
yum makecache
yum install -y patchman patchman-client
systemctl restart httpd
patchman-manage createsuperuser
```

### virtualenv + pip

TBD - not working yet

```shell
apt -y install gcc libxml2-dev libxslt1-dev virtualenv python-dev zlib1g-dev  # (debian/ubuntu)
yum -y install gcc libxml2-devel libxslt-devel python-virtualenv              # (centos/rhel)
mkdir /srv/patchman
cd /srv/patchman
virtualenv .
. bin/activate
pip install --upgrade pip
pip install patchman gunicorn whitenoise==3.3.1
patchman-manage migrate
patchman-manage createsuperuser
gunicorn patchman.wsgi -b 0.0.0.0:80
```

### Source

#### Ubuntu 18.04 (bionic)

1. Install dependencies

```shell
apt -y install python-django-tagging python-django python-requests \
python-django-extensions python-argparse python-defusedxml python-rpm python-debian \
python-pygooglechart python-cracklib python-progressbar libapache2-mod-wsgi \
python-djangorestframework apache2 python-colorama python-humanize liblzma-dev \
python-magic python-lxml
```

2. Install django-bootstrap3

```shell
pip install django-bootstrap3==11.1.0
```

3. Clone git repo to e.g. /srv/patchman

```shell
cd /srv
git clone https://github.com/furlongm/patchman
```

4. Copy server settings example file to /etc/patchman

```shell
mkdir /etc/patchman
cp /srv/patchman/etc/patchman/local_settings.py /etc/patchman/
```

# Configuration

## Patchman Settings

Modify `/etc/patchman/local_settings.py` to configure patchman.

If installing from source or using virtualenv, the following settings should
be configured:

   * ADMINS - set up an admin email address
   * SECRET_KEY - create a random secret key
   * STATICFILES_DIRS - should point to /srv/patchman/patchman/static if installing from
     source


## Configure Database

The default database backend is sqlite. However, this is not recommended for
production deployments. MySQL or PostgreSQL are better choices.

### SQLite

To configure the sqlite database backend:

1. Create the database directory specified in the settings file:

```shell
mkdir -p /var/lib/patchman/db
```

2. Modify `/etc/patchman/local_settings.py` as follows:

```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/var/lib/patchman/db/patchman.db'
    }
}
```

3. Proceed to syncing database.


### MySQL

To configure the mysql database backend:

1. Ensure mysql-server and the python mysql bindings are installed:

```shell
apt -y install default-mysql-server python-mysqldb python-pymysql
```

2. Create database and users:
```
$ mysql

mysql> CREATE DATABASE patchman CHARACTER SET utf8 COLLATE utf8_general_ci;
Query OK, 1 row affected (0.00 sec)

mysql> GRANT ALL PRIVILEGES ON patchman.* TO patchman@localhost IDENTIFIED BY 'changeme';
Query OK, 0 rows affected (0.00 sec)
```

3. Modify `/etc/patchman/local_settings.py` as follows:

```
DATABASES = {
   'default': {
       'ENGINE': 'django.db.backends.mysql',
       'NAME': 'patchman',
       'USER': 'patchman',
       'PASSWORD': 'changeme',
       'HOST': '',
       'PORT': '',
       'STORAGE_ENGINE': 'INNODB',
       'CHARSET' : 'utf8'
   }
}
```

4. Proceed to syncing database.


### PostgreSQL

To configure the postgresql database backend:

1. Ensure the postgresql server and the python postgres bindings are installed:

```shell
apt -y install postgresql python-psycopg2
```

2. Create database and users:
```
$ sudo su - postgres
$ psql

postgres=# CREATE DATABASE patchman;
CREATE DATABASE
postgres=# CREATE USER patchman WITH PASSWORD 'changeme';
CREATE ROLE
postgres=# ALTER ROLE patchman SET client_encoding TO 'utf8';
ALTER ROLE
postgres=# ALTER ROLE patchman SET default_transaction_isolation TO 'read committed';
ALTER ROLE
postgres=# ALTER ROLE patchman SET timezone TO 'UTC';
ALTER ROLE
postgres=# GRANT ALL PRIVILEGES ON DATABASE patchman to patchman;
GRANT
```

3. Modify `/etc/patchman/local_settings.py` as follows:

```
DATABASES = {
   'default': {
       'ENGINE': 'django.db.backends.postgresql_psycopg2',
       'NAME': 'patchman',
       'USER': 'patchman',
       'PASSWORD': 'changeme',
       'HOST': '127.0.0.1',
       'PORT': '',
       'CHARSET' : 'utf8'
   }
}
```

4. Proceed to syncing database.


### Sync Database

After configuring a database backend, the django database should be synced:

1. Initialise the database, perform migrations, create the admin user and
collect static files:

```shell
patchman-manage makemigrations
patchman-manage migrate --run-syncdb
patchman-manage createsuperuser
patchman-manage collectstatic
```

N.B. To run patchman-manage when installing from source, run `./manage.py`


2. Restart the web server after syncing the database.


## Configure Web Server

### Apache

1. If installing from source, enable mod-wsgi and copy the apache conf file:

```shell
a2enmod wsgi
cp /srv/patchman/etc/patchman/apache.conf.example /etc/apache2/conf-available/patchman.conf
a2enconf patchman
```

2. Edit the networks allowed to report to apache and reload apache.

```shell
vi /etc/apache2/conf-available/patchman.conf
service apache2 reload
```

3. If installing from source, allow apache access to the settings and to the sqlite db:

```shell
chown -R :www-data /etc/patchman
chmod -R g+r /etc/patchman
chown -R :www-data /var/lib/patchman
chmod -R g+w /var/lib/patchman/db
```

The django interface should be available at http://127.0.0.1/patchman/

## Optional Configuration Items

### Cronjobs

#### Daily cronjob on patchman server

A daily cronjob on the patchman server should be run to process reports,
perform database maintenance, check for upstream updates, and find updates for
clients.

```
patchman -a
```

#### Daily cronjob on client to send reports to patchman server

```
patchman-client
```

### Celery

Install Celery for realtime processing of reports from clients:

#### Ubuntu / Debian

```shell
apt -y install python-celery python-celery-common rabbitmq-server
C_FORCE_ROOT=1 celery worker --loglevel=info -E -A patchman
```

#### CentOS / RHEL

```shell
yum -y install python-celery rabbitmq-server
systemctl restart rabbitmq-server
semanage port -a -t http_port_t -p tcp 5672
C_FORCE_ROOT=1 celery worker --loglevel=info -E -A patchman

```

Add the last command to an initscript (e.g. /etc/rc.local) to make celery
persistent over reboot.

### Memcached

Memcached can optionally be run to reduce the load on the server.

```shell
apt -y install memcached python-memcache   # (debian/ubuntu)
yum -y install memcached python-memcached  # (centos/rhel)
systemctl restart memcached
```

and add the following to `/etc/patchman/local_settings.py`

```
CACHES = {
   'default': {
       'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
       'LOCATION': '127.0.0.1:11211',
   }
}
```

# Test Installation

To test the installation, run the client locally on the patchman server:

```shell
patchman-client -s http://127.0.0.1/patchman/
```
