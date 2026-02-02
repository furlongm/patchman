# Copyright 2025 Marcus Furlong <furlongm@gmail.com>
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

from django.test import TestCase, override_settings
from django.utils import timezone

from errata.models import Erratum
from operatingsystems.models import OSRelease
from security.models import CVE


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ErratumMethodTests(TestCase):
    """Tests for Erratum model methods."""

    def test_erratum_creation(self):
        """Test creating an Erratum."""
        erratum = Erratum.objects.create(
            name='USN-1234-1',
            e_type='security',
            synopsis='Security update',
            issue_date=timezone.now(),
        )
        self.assertEqual(erratum.name, 'USN-1234-1')

    def test_erratum_str(self):
        """Test Erratum __str__ method."""
        erratum = Erratum.objects.create(
            name='USN-1234-1',
            e_type='security',
            synopsis='Security update',
            issue_date=timezone.now(),
        )
        self.assertIn('USN-1234-1', str(erratum))

    def test_erratum_get_absolute_url(self):
        """Test Erratum.get_absolute_url()."""
        erratum = Erratum.objects.create(
            name='USN-1234-1',
            e_type='security',
            synopsis='Security update',
            issue_date=timezone.now(),
        )
        url = erratum.get_absolute_url()
        self.assertIn(erratum.name, url)

    def test_erratum_unique_name(self):
        """Test Erratum name is unique."""
        Erratum.objects.create(
            name='USN-1234-1',
            e_type='security',
            synopsis='Security update',
            issue_date=timezone.now(),
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Erratum.objects.create(
                name='USN-1234-1',
                e_type='bugfix',
                synopsis='Bugfix update',
                issue_date=timezone.now(),
            )

    def test_erratum_with_cves(self):
        """Test Erratum with associated CVEs."""
        erratum = Erratum.objects.create(
            name='USN-1234-1',
            e_type='security',
            synopsis='Security update',
            issue_date=timezone.now(),
        )
        cve = CVE.objects.create(cve_id='CVE-2024-12345')
        erratum.cves.add(cve)
        self.assertIn(cve, erratum.cves.all())

    def test_erratum_with_osreleases(self):
        """Test Erratum with associated OS releases."""
        erratum = Erratum.objects.create(
            name='USN-1234-1',
            e_type='security',
            synopsis='Security update',
            issue_date=timezone.now(),
        )
        release = OSRelease.objects.create(name='Ubuntu 22.04')
        erratum.osreleases.add(release)
        self.assertIn(release, erratum.osreleases.all())

    def test_security_erratum(self):
        """Test creating a security erratum."""
        erratum = Erratum.objects.create(
            name='RHSA-2024:1234',
            e_type='security',
            synopsis='Important security update',
            issue_date=timezone.now(),
        )
        self.assertEqual(erratum.e_type, 'security')

    def test_bugfix_erratum(self):
        """Test creating a bugfix erratum."""
        erratum = Erratum.objects.create(
            name='RHBA-2024:1234',
            e_type='bugfix',
            synopsis='Bug fix update',
            issue_date=timezone.now(),
        )
        self.assertEqual(erratum.e_type, 'bugfix')
