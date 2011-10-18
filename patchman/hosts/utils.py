from patchman.hosts.signals import host_update_found
from patchman.hosts.models import Host


def find_host_updates(host=None, verbose=0):

    update_hosts = []

    if host:
        try:
            update_hosts.append(Host.objects.get(hostname=host))
            message = 'Finding updates for host %s' % host
        except:
            message = 'Host %s does not exist' % host
    else:
        message = 'Finding updates for all hosts'
        update_hosts = Host.objects.all()

    if verbose:
        print message

    for host in update_hosts:
        if verbose:
            print '\n%s' % host
        host.find_updates()
        