# Patchman Docker Image
This is the first version of Patchman Docker image. This version assumes that Postgres is the database of choice.

## Configuration Environment Variables
The following table contains all environment variables which can be set to Patchman container during runtime.

| Variable               | Description                                                                                                                                                          | Default    |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| **Django Related**     |                                                                                                                                                                      |            |
| `DJANGO_SECRET_KEY`    | The unique `SECRET_KEY` strin of patchman application                                                                                                                | `nil`      |
| `DJANGO_DEBUG`         | Run Patchman in debug mode                                                                                                                                           | `false`    |
| `DJANGO_LOGLEVEL`      | One of `debug`, `info`, `warning`, `error`, `critical`                                                                                                               | `info`     |
| `DJANGO_ALLOWED_HOSTS` | Hosts allowed to be part of HTTP Headers of incoming requests                                                                                                        | `*`        |
| `DJANGO_ADMINS`        | A comma separated list of Patchman administrators in format `Name;Surname;mail@example.com`. It sets `ADMINS` and `MANAGERS` Django Settings for email notifications | `nil`      |
| **Postgres Related**   |                                                                                                                                                                      |            |
| `DATABASE_HOST`        | postgres service name                                                                                                                                                | `nil`      |
| `DATABASE_PORT`        | postgres service port                                                                                                                                                | `5432`     |
| `DATABASE_NAME`        | postgres database name                                                                                                                                               | `patchman` |
| `DATABASE_USERNAME`    | postgres database username                                                                                                                                           | `patchman` |
| `DATABASE_PASSWORD`    | postgres database password                                                                                                                                           | `patchman` |
| **Memcached Related**  |                                                                                                                                                                      |            |
| `MEMCACHED_HOST`       | memcached service name                                                                                                                                               | `nil`      |
| `MEMCACHED_PORT`       | memcached service port                                                                                                                                               | `11211`    |
