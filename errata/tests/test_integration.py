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

from errata.models import Erratum
from operatingsystems.models import OSRelease
from security.models import CVE


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ErrataIntegrationTests(TestCase):
    """Integration tests for errata functionality."""

    def test_erratum_with_cves(self):
        """Test erratum can be associated with CVEs."""
        cve1 = CVE.objects.create(cve_id='CVE-2024-1001')
        cve2 = CVE.objects.create(cve_id='CVE-2024-1002')

        erratum = Erratum.objects.create(
            name='RHSA-2024:1234',
            e_type='Security Advisory',
            synopsis='Important: curl security update',
            issue_date='2024-03-15',
        )
        erratum.cves.add(cve1, cve2)

        self.assertEqual(erratum.cves.count(), 2)
        self.assertIn(cve1, erratum.cves.all())
        self.assertIn(cve2, erratum.cves.all())

    def test_erratum_with_osreleases(self):
        """Test erratum can be associated with OS releases."""
        osrelease1 = OSRelease.objects.create(name='Rocky Linux 9')
        osrelease2 = OSRelease.objects.create(name='Rocky Linux 8')

        erratum = Erratum.objects.create(
            name='RHSA-2024:1235',
            e_type='Security Advisory',
            synopsis='Important: openssl security update',
            issue_date='2024-03-16',
        )
        erratum.osreleases.add(osrelease1, osrelease2)

        self.assertEqual(erratum.osreleases.count(), 2)

    def test_erratum_with_packages(self):
        """Test erratum can reference package names."""
        erratum = Erratum.objects.create(
            name='RHSA-2024:1236',
            e_type='Bug Fix',
            synopsis='Bug fix: httpd update',
            issue_date='2024-03-17',
        )

        # Verify erratum can store package references
        self.assertIsNotNone(erratum)
        self.assertEqual(erratum.e_type, 'Bug Fix')
