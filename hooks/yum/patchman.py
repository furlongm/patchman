import os

from yum.plugins import TYPE_CORE

requires_api_version = '2.1'
plugin_type = (TYPE_CORE,)


def posttrans_hook(conduit):
    conduit.info(2, 'patchman: sending data')
    servicecmd = conduit.confString('main', 'servicecmd', '/usr/sbin/patchman-client')
    args = '-n'
    command = '{0!s} {1!s}> /dev/null'.format(servicecmd, args)
    os.system(command)
