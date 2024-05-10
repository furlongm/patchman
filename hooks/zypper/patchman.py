#!/usr/bin/env python3
#
# Copyright 2024 Marcus Furlong <furlongm@gmail.com>
#
# This file is part of Patchman.
#
# Patchman is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 only.
#
# Patchman is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchman. If not, see <http://www.gnu.org/licenses/>
#
# zypp system plugin for patchman

import logging
import os
import sys
from zypp_plugin import Plugin


class MyPlugin(Plugin):

    def PACKAGESETCHANGED(self, headers, body):
        s = 'Sending report to patchman server...'
        logging.info(s)
        sys.stderr.write(s)
        servicecmd = '/usr/sbin/patchman-client'
        args = '-n'
        command = f'{servicecmd} {args}'
        os.system(command)
        self.ack()


plugin = MyPlugin()
plugin.main()
