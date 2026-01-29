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

# temporary fix for 'database is locked' error on sqlite3
# can be removed when using django 5.1 and BEGIN IMMEDIATE in OPTIONS
# see https://blog.pecar.me/django-sqlite-dblock for more details

from django.db.backends.sqlite3 import base


class DatabaseWrapper(base.DatabaseWrapper):
    def _start_transaction_under_autocommit(self):
        # Acquire a write lock immediately for transactions
        self.cursor().execute('BEGIN IMMEDIATE')
