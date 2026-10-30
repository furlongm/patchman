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

import importlib.util
from datetime import timedelta
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from reports.models import Report


def load_cli():
    path = Path(__file__).resolve().parents[2] / 'sbin' / 'patchman'
    loader = SourceFileLoader('patchman_cli', str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module


class ProcessReportsCLITests(TestCase):
    """Tests for process_reports() in sbin/patchman."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cli = load_cli()

    def _report(self, host, days_ago, processed):
        report = Report.objects.create(host=host, processed=processed)
        Report.objects.filter(pk=report.pk).update(created=timezone.now() - timedelta(days=days_ago))
        return report

    def setUp(self):
        self.a_old = self._report('a.example.com', 3, True)
        self.a_new = self._report('a.example.com', 2, True)
        self.b_old = self._report('b.example.com', 2, False)
        self.b_new = self._report('b.example.com', 1, False)

    def _processed(self, **kwargs):
        with mock.patch.object(Report, 'process', autospec=True) as process:
            self.cli.process_reports(**kwargs)
        return [(c.args[0], c.kwargs['force']) for c in process.call_args_list]

    def test_pending_reports_oldest_first(self):
        self.assertEqual(self._processed(), [(self.b_old, False), (self.b_new, False)])

    def test_force_selects_latest_report_per_host(self):
        self.assertEqual(self._processed(force=True), [(self.a_new, True), (self.b_new, True)])

    def test_force_with_host(self):
        self.assertEqual(self._processed(host='a.example.com', force=True), [(self.a_new, True)])
