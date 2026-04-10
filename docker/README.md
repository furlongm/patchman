Source: https://github.com/ricardojeronimo/patchman

Upstream: https://github.com/furlongm/patchman


## Getting Started

To get started, pull the latest image from Docker Hub and run it.
```
docker pull ricardojeronim0/patchman:latest
docker run -d -p 80:80 --name patchman ricardojeronim0/patchman
```

This container will run migrations on first startup, but you still need to create a superuser before being able to log in on the web interface.

```
docker exec -it patchman patchman-manage createsuperuser
```

## Configuration

This container is configured using environment variables. The following variables are available to customize the container's behavior.

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DEBUG` | `False` | Debug mode |
| `ADMIN_NAME` | `Your Name` | Your name |
| `ADMIN_EMAIL` | `you@example.com` | Your e-mail address |
| `TIMEZONE` | `America/New_York` | Your timezone |
| `LANGUAGE_CODE` | `en-us` | Your language |
| `SECRET_KEY` |  | Unique string not to be shared with anyone. Leave empty to generate one randomly |
| `MAX_MIRRORS` | `2` | Maximum number of mirrors to add or refresh per repo |
| `MAX_MIRROR_FAILURES` | `14` |  Maximum number of failures before disabling a mirror, set to `-1` to never disable mirrors |
| `DAYS_WITHOUT_REPORT` | `14` | Number of days to wait before raising that a host has not reported |
| `ERRATA_OS_UPDATES` | `yum, rocky, alma, arch, ubuntu, debian` | List of errata sources to update, remove unwanted ones to improve performance  |
| `ALMA_RELEASES` | `8, 9, 10` | List of Alma Linux releases to update |
| `DEBIAN_CODENAMES` | `bookworm, trixie` | List of Debian Linux releases to update |
| `UBUNTU_CODENAMES` | `jammy, noble` | List of Ubuntu Linux releases to update |
| `DB_ENGINE` | `SQLite` | Database engine to be used. Choose between `MySQL` or `PostgreSQL`, leave empty to use default `SQLite` |
| `DB_HOST` |  | Database hostname, IP or container name |
| `DB_PORT` |  | Database port |
| `DB_DATABASE` |  | Database name |
| `DB_USER` |  | Database user |
| `DB_PASSWORD` |  | Database password |
| `REDIS_HOST` | `127.0.0.1` | Redis hostname, IP or container name |
| `REDIS_PORT` | `6379` | Redis port |
| `USE_CELERY` | `False` | Change to `True` for realtime processing of reports from clients |
| `USE_CACHE` | `False` | Change to `True` cache contents and reduce the load on the server |
| `CACHE_TIMEOUT` | `30` | Cache time in seconds. Be aware that the UI results may be out of date for this amount of time |


## Docker Compose Example

For more complex deployments, `docker-compose` is the recommended approach. Below is an example `docker-compose.yaml` file that demonstrates how to configure the container and connect it to a separate MySQL service, and Redis for async processing and/or caching.

```yaml
---
services:
  patchman:
    container_name: patchman
    image: ricardojeronim0/patchman:latest 
    restart: unless-stopped
    environment:
      ADMIN_NAME: admin_name
      ADMIN_EMAIL: admin_mail@domain.tld
      TIMEZONE: America/New_York
      DB_ENGINE: MySQL
      DB_HOST: patchman-db
      DB_PORT: 3306
      DB_DATABASE: patchman
      DB_USER: user
      DB_PASSWORD: changeme
      REDIS_HOST: redis
      REDIS_PORT: 6379
      USE_CELERY: True
      USE_CACHE: True
      CACHE_TIMEOUT: 20
    ports:
      - 80:80/tcp
    depends_on:
      - patchman-db
      - redis

  patchman-db:
    container_name: patchman-db
    image: mysql:latest
    restart: unless-stopped
    command: ["mysqld", "--character-set-server=utf8", "--collation-server=utf8_general_ci"]
    environment:
      MYSQL_ROOT_PASSWORD: changeme 
      MYSQL_DATABASE: patchman 
      MYSQL_USER: user
      MYSQL_PASSWORD: changeme

  redis:
    container_name: redis
    image: redis:latest
    restart: unless-stopped
```
