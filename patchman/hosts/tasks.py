from patchman.hosts.utils import find_host_updates as find_host_updates_real

from celery.decorators import task

@task()
def find_host_updates(host):
    find_host_updates_real(host)

        