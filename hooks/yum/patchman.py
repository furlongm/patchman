import os
from glob import fnmatch

import yum
from yum.plugins import PluginYumExit, TYPE_CORE

requires_api_version = '2.1'
plugin_type = (TYPE_CORE,)

def posttrans_hook(conduit):
    conduit.info(2, 'patchman: sending data')
    servicecmd = conduit.confString('main', 'servicecmd', '/usr/sbin/patchman-client')
    args = '-n'
    command = '%s %s> /dev/null' % (servicecmd, args)
    os.system(command)
