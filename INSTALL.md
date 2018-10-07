# Installation

## Install Options
  - [deb/apt](#deb--apt)
  - [git](#git)

### deb/apt

#### Ubuntu 16.04 (xenial)

```shell
apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0412F522
echo "deb http://repo.openbytes.ie/ubuntu xenial main" > /etc/apt/sources.list.d/patchman.list
apt-get update
apt-get install python-patchman patchman-client
```

#### Debian 9 (stretch)

```shell
apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0412F522
echo "deb http://repo.openbytes.ie/debian stretch main" > /etc/apt/sources.list.d/patchman.list
echo "deb http://http.debian.net/debian stretch-backports main contrib non-free" > /etc/apt/sources.list.d/backports.list
apt-get update
apt-get install python-patchman patchman-client
```

### git

#### Ubuntu 16.04 (xenial)

1. Install dependencies
```shell
apt-get install python-django-tagging python-django python-requests \
python-django-extensions python-argparse python-lxml python-rpm python-debian \
python-pygooglechart python-cracklib python-progressbar libapache2-mod-wsgi \
python-djangorestframework apache2 python-colorama python-humanize liblzma-dev
```

2. Install django-bootstrap3
```shell
pip install django-bootstrap3
```

3. Clone git repo to e.g. /srv/patchman
```shell
cd /srv
git clone https://github.com/furlongm/patchman
```

4. Copy server settings example file to /etc/patchman
```shell
mkdir /etc/patchman
cp /srv/patchman/etc/local_settings.py /etc/patchman/
```

# Configuration

## Patchman Settings

 Modify the patchman settings file to suit your site
```shell
vi /etc/patchman/local_settings.py
```

Some things that should be added or modified:

   * ADMINS
   * SECRET_KEY
   * Change STATICFILES_DIRS to /srv/patchman/media if installing from git
   * Configure database backend. Default is sqlite, instructions for mysql are below

Once the settings are configured, create the database:

```shell
patchman-manage makemigrations
patchman-manage migrate --run-syncdb
```

## Configure Database

### sqlite

The default database is sqlite.

### MySQL

1. To configure the mysql backend:

Make sure mysql-server and the python mysql bindings are installed:

```shell
apt-get install mysql-server python-mysqldb python-pymysql
```

2. Create database and users:
```
mysql> CREATE DATABASE patchman CHARACTER SET utf8 COLLATE utf8_general_ci;
Query OK, 1 row affected (0.00 sec)

mysql> GRANT ALL PRIVILEGES ON patchman.* TO patchman@localhost IDENTIFIED BY 'changeme';
Query OK, 0 rows affected (0.00 sec)
```

3. Modify /etc/patchman/local_settings.py as follows:

```
DATABASES = {
   'default': {
       'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
       'NAME': 'patchman',                   # Or path to database file if using sqlite3.
       'USER': 'patchman',                   # Not used with sqlite3.
       'PASSWORD': 'changeme',               # Not used with sqlite3.
       'HOST': '',                           # Set to empty string for localhost. Not used with sqlite3.
       'PORT': '',                           # Set to empty string for default. Not used with sqlite3.
       'STORAGE_ENGINE': 'INNODB',
       'CHARSET' : 'utf8'
   }
}
```

### Sync Database

1. Initialise the database, perform migrations, and collect static files
```shell
cd /srv/patchman/patchman
./manage.py syncdb # answer questions here if required
./manage.py collectstatic
```

## Configure Webserver

### Apache

1. Enable mod-wsgi and copy the apache conf file:
```shell
a2enmod wsgi
cp /srv/patchman/etc/patchman-apache.conf /etc/apache2/conf-available/patchman.conf
a2enconf patchman
```

2. Edit the networks allowed to report to apache and reload apache.
```shell
vi /etc/apache2/conf-available/patchman.conf
service apache2 reload
```

The django interface should be available at http://127.0.0.1/patchman/

### Optional Configuration Items

#### Cronjobs

#### Daily cronjob on patchman server
You should run a daily job on the patchman server to process reports, perform
database maintenance, check for upstream updates, and find updates for clients.

```
patchman -a
```

#### Daily cronjob on client to send reports to patchman server

```
patchman-client
```

#### Celery

Install celeryd for realtime processing of reports from clients:

```shell
apt-get install python-django-celery rabbitmq-server
./manage.py syncdb
./manage.py celeryd_detach
```

Add the last command to an initscript (e.g. /etc/rc.local) to make celery
persistent over reboot.

#### Memcached

You can optionally enable memcached:
```shell
apt-get install memcached python-memcache
```

and add the following to /etc/patchman/local_settings.py
```
CACHES = {
   'default': {
       'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
       'LOCATION': '127.0.0.1:11211',
   }
}
```

#### Test installation
To test your installation, run the client locally on the patchman server:
```shell
patchman-client -s http://127.0.0.1/patchman/
````
