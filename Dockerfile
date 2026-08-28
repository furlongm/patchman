DockerfileFROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libpq-dev \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn whitenoise psycopg2-binary

COPY . .

# Overwrite the local_settings.py with the Docker-specific one.
# settings.py resolves conf_path to ./etc/patchman when running from source.
COPY docker/local_settings.py /app/etc/patchman/local_settings.py

RUN mkdir -p /var/lib/patchman/static

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
