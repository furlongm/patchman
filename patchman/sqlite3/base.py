# temporary fix for 'database is locked' error on sqlite3
# can be removed when using django 5.1 and BEGIN IMMEDIATE in OPTIONS
# see https://blog.pecar.me/django-sqlite-dblock for more details

from django.db.backends.sqlite3 import base


class DatabaseWrapper(base.DatabaseWrapper):
    def _start_transaction_under_autocommit(self):
        # Acquire a write lock immediately for transactions
        self.cursor().execute('BEGIN IMMEDIATE')
