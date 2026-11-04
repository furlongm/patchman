# Copyright 2026 Marcus Furlong <furlongm@gmail.com>
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

import json
from importlib import import_module

from django.apps import apps
from django.db import connection
from django.test import TransactionTestCase, override_settings

from hosts.models import Host
from reports.models import Report

migration = import_module('hosts.migrations.0014_drop_legacy_tagging')


def host_columns():
    with connection.cursor() as cursor:
        return [c.name for c in connection.introspection.get_table_description(cursor, 'hosts_host')]


def table_names():
    with connection.cursor() as cursor:
        return connection.introspection.table_names(cursor)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class DropLegacyTaggingTests(TransactionTestCase):
    """Tests for hosts migration 0014 (leftover django-tagging schema, #690)."""

    def setUp(self):
        self.addCleanup(self.run_migration)

    def run_migration(self):
        with connection.schema_editor() as schema_editor:
            migration.drop_legacy_tagging(apps, schema_editor)

    def add_legacy_schema(self):
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE hosts_host ADD COLUMN tags varchar(255) CHECK (tags IS NOT NULL)')
            cursor.execute('CREATE TABLE tagging_tag (id integer PRIMARY KEY, name varchar(50))')
            cursor.execute(
                'CREATE TABLE tagging_taggeditem '
                '(id integer PRIMARY KEY, tag_id integer REFERENCES tagging_tag (id))'
            )

    def create_report(self):
        return Report.objects.create(
            host='legacy.example.com',
            domain='example.com',
            report_ip='192.168.1.10',
            os='Ubuntu 22.04.3 LTS',
            kernel='5.15.0-91-generic',
            arch='x86_64',
            protocol='2',
            packages=json.dumps([]),
            repos=json.dumps([]),
            modules=json.dumps([]),
            sec_updates=json.dumps([]),
            bug_updates=json.dumps([]),
        )

    def test_legacy_column_does_not_crash_report_processing(self):
        """Host creation fails on the legacy column; process() must not raise."""
        self.add_legacy_schema()
        self.create_report().process(find_updates=False)
        self.assertFalse(Host.objects.filter(hostname='legacy.example.com').exists())

    def test_drops_legacy_column_and_tables(self):
        """Leftover tags column and tagging tables are dropped; hosts can be created again."""
        self.add_legacy_schema()
        self.run_migration()
        self.assertNotIn('tags', host_columns())
        self.assertNotIn('tagging_tag', table_names())
        self.assertNotIn('tagging_taggeditem', table_names())
        self.create_report().process(find_updates=False)
        self.assertTrue(Host.objects.filter(hostname='legacy.example.com').exists())

    def test_noop_on_clean_schema(self):
        """Fresh installs have nothing to drop."""
        before = host_columns()
        self.run_migration()
        self.assertEqual(host_columns(), before)
