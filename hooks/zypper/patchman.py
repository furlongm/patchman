#!/usr/bin/env python
#
# Copyright 2016 Marcus Furlong <furlongm@gmail.com>
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
#
import os
import logging
from zypp_plugin import Plugin


class MyPlugin(Plugin):

    def PLUGINBEGIN(self, headers, body):
        logging.info('PLUGINBEGIN')
        logging.debug(f'headers: {headers!s}')
        self.ack()

    def PACKAGESETCHANGED(self, headers, body):
        logging.info('PACKAGESETCHANGED')
        logging.debug(f'headers: {headers!s}')
        print('patchman: sending data')
        servicecmd = '/usr/sbin/patchman-client'
        args = '-n'
        command = f'{servicecmd!s} {args!s}> /dev/null'
        os.system(command)
        self.ack()

    def PLUGINEND(self, headers, body):
        logging.info('PLUGINEND')
        logging.debug(f'headers: {headers!s}')
        self.ack()


plugin = MyPlugin()
plugin.main()
