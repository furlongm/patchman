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

from datetime import datetime, timezone

from defusedxml import ElementTree
from django.test import TestCase

from errata.sources.repos.yum import get_updateinfo_issue_date


def make_update(dates):
    return ElementTree.fromstring(f'<update type="security"><id>TEST-1</id>{dates}</update>')


class UpdateinfoIssueDateTests(TestCase):
    """Tests for getting the issue date of an updateinfo erratum."""

    def test_issued_date(self):
        """Test the issued date is used when present."""
        update = make_update('<issued date="2026-08-26 12:34:56"/><updated date="2026-09-01 00:00:00"/>')
        self.assertEqual(
            get_updateinfo_issue_date(update),
            datetime(2026, 8, 26, 12, 34, 56, tzinfo=timezone.utc),
        )

    def test_falls_back_to_updated_date(self):
        """Test the updated date is used when there is no issued date."""
        update = make_update('<updated date="2026-09-01 00:00:00 UTC"/>')
        self.assertEqual(get_updateinfo_issue_date(update), datetime(2026, 9, 1, tzinfo=timezone.utc))

    def test_falls_back_when_issued_invalid(self):
        """Test the updated date is used when the issued date is invalid."""
        update = make_update('<issued date="bogus"/><updated date="1704067200"/>')
        self.assertEqual(get_updateinfo_issue_date(update), datetime(2024, 1, 1, tzinfo=timezone.utc))

    def test_no_valid_date(self):
        """Test None is returned when there is no valid date."""
        self.assertIsNone(get_updateinfo_issue_date(make_update('<issued/>')))
