# How to use this docker-compose

## Run the docker compose

```
$ docker-compose up -d
Creating network "docker_default" with the default driver
Creating volume "docker_my-db" with default driver
Creating docker_patchman_1 ... done
Creating docker_database_1 ... done
```

## Check if DB migrations applied and apache2 started

```
$ docker logs docker_patchman_1
Waiting for database connection...
Waiting for database connection...
No changes detected
Operations to perform:
  Synchronize unmigrated apps: admindocs, arch, bootstrap3, django_extensions, domains, hosts, humanize, messages, operatingsystems, packages, reports, repos, rest_framework, staticfiles, util
  Apply all migrations: admin, auth, contenttypes, sessions, sites, tagging
Synchronizing apps without migrations:
  Creating tables...
    Creating table arch_machinearchitecture
    Creating table arch_packagearchitecture
    Creating table domains_domain
    Creating table hosts_host
    Creating table hosts_hostrepo
    Creating table operatingsystems_osgroup
    Creating table operatingsystems_os
    Creating table packages_packagename
    Creating table packages_package
    Creating table packages_packageupdate
    Creating table packages_erratumreference
    Creating table packages_erratum
    Creating table repos_repository
    Creating table repos_mirror
    Creating table repos_mirrorpackage
    Creating table reports_report
    Running deferred SQL...
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
  Applying admin.0002_logentry_remove_auto_add... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0002_alter_permission_name_max_length... OK
  Applying auth.0003_alter_user_email_max_length... OK
  Applying auth.0004_alter_user_username_opts... OK
  Applying auth.0005_alter_user_last_login_null... OK
  Applying auth.0006_require_contenttypes_0002... OK
  Applying auth.0007_alter_validators_add_error_messages... OK
  Applying auth.0008_alter_user_username_max_length... OK
  Applying sessions.0001_initial... OK
  Applying sites.0001_initial... OK
  Applying sites.0002_alter_domain_unique... OK
  Applying tagging.0001_initial... OK
  Applying tagging.0002_on_delete... OK

0 static files copied to '/var/lib/patchman/static', 111 unmodified.
AH00558: apache2: Could not reliably determine the server's fully qualified domain name, using 192.168.160.2. Set the 'ServerName' directive globally to suppress this message
```

## Create superuser for Django

```
$ docker exec -it docker_patchman_1 patchman-manage createsuperuser

Username (leave blank to use 'root'): admin
Email address: admin@example.com
Password:
Password (again):
Superuser created successfully.
```
