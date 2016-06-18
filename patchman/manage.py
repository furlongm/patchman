#!/usr/bin/env python

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

import os
import sys

if __name__ == '__main__':

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'patchman.settings')

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
