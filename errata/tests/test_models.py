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
from security.models import CVE, Reference


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


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ErratumCachedCountTests(TestCase):
    """Tests for Erratum cached count fields and M2M signals."""

    def setUp(self):
        self.erratum = Erratum.objects.create(
            name='USN-5678-1',
            e_type='security',
            synopsis='Security update',
            issue_date=timezone.now(),
        )

    def test_initial_counts_are_zero(self):
        """Test that cached counts start at zero."""
        self.assertEqual(self.erratum.cves_count, 0)
        self.assertEqual(self.erratum.osreleases_count, 0)
        self.assertEqual(self.erratum.affected_packages_count, 0)
        self.assertEqual(self.erratum.fixed_packages_count, 0)
        self.assertEqual(self.erratum.references_count, 0)

    def test_cves_count_on_add(self):
        """Test cves_count increments on add."""
        cve1 = CVE.objects.create(cve_id='CVE-2024-0001')
        cve2 = CVE.objects.create(cve_id='CVE-2024-0002')
        self.erratum.cves.add(cve1)
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.cves_count, 1)
        self.erratum.cves.add(cve2)
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.cves_count, 2)

    def test_cves_count_on_remove(self):
        """Test cves_count decrements on remove."""
        cve = CVE.objects.create(cve_id='CVE-2024-0003')
        self.erratum.cves.add(cve)
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.cves_count, 1)
        self.erratum.cves.remove(cve)
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.cves_count, 0)

    def test_cves_count_on_clear(self):
        """Test cves_count resets to zero on clear."""
        cve1 = CVE.objects.create(cve_id='CVE-2024-0004')
        cve2 = CVE.objects.create(cve_id='CVE-2024-0005')
        self.erratum.cves.add(cve1, cve2)
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.cves_count, 2)
        self.erratum.cves.clear()
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.cves_count, 0)

    def test_osreleases_count_on_add(self):
        """Test osreleases_count increments on add."""
        release = OSRelease.objects.create(name='Ubuntu 24.04')
        self.erratum.osreleases.add(release)
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.osreleases_count, 1)

    def test_osreleases_count_on_remove(self):
        """Test osreleases_count decrements on remove."""
        release = OSRelease.objects.create(name='Ubuntu 24.04')
        self.erratum.osreleases.add(release)
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.osreleases_count, 1)
        self.erratum.osreleases.remove(release)
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.osreleases_count, 0)

    def test_references_count_on_add(self):
        """Test references_count increments on add."""
        ref = Reference.objects.create(
            ref_type='ADVISORY',
            url='https://example.com/advisory/1',
        )
        self.erratum.references.add(ref)
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.references_count, 1)

    def test_references_count_on_remove(self):
        """Test references_count decrements on remove."""
        ref = Reference.objects.create(
            ref_type='ADVISORY',
            url='https://example.com/advisory/2',
        )
        self.erratum.references.add(ref)
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.references_count, 1)
        self.erratum.references.remove(ref)
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.references_count, 0)

    def test_str_uses_cached_counts(self):
        """Test __str__ reflects cached count values."""
        cve = CVE.objects.create(cve_id='CVE-2024-0010')
        release = OSRelease.objects.create(name='RHEL 9')
        self.erratum.cves.add(cve)
        self.erratum.osreleases.add(release)
        self.erratum.refresh_from_db()
        result = str(self.erratum)
        self.assertIn('1 related CVEs', result)
        self.assertIn('affecting 1 OS Releases', result)
        self.assertIn('providing 0 fixed Packages', result)

    def test_counts_match_actual_m2m(self):
        """Test cached counts stay in sync with actual M2M counts."""
        cve1 = CVE.objects.create(cve_id='CVE-2024-0020')
        cve2 = CVE.objects.create(cve_id='CVE-2024-0021')
        release = OSRelease.objects.create(name='Debian 12')
        self.erratum.cves.add(cve1, cve2)
        self.erratum.osreleases.add(release)
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.cves_count, self.erratum.cves.count())
        self.assertEqual(self.erratum.osreleases_count, self.erratum.osreleases.count())

    def test_add_fixed_packages_no_stale_save(self):
        """Test that add_fixed_packages does not overwrite cached counts.

        Regression test: add_fixed_packages previously called self.save()
        after the M2M .add() loop, which overwrote the signal-updated
        fixed_packages_count with the stale in-memory value.
        """
        from arch.models import PackageArchitecture
        from packages.models import Package, PackageName
        pkg_arch = PackageArchitecture.objects.create(name='amd64')
        pkg_name = PackageName.objects.create(name='libssl3')
        pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='3.0.1', release='1', packagetype='D'
        )
        self.erratum.add_fixed_packages({pkg})
        self.erratum.refresh_from_db()
        self.assertEqual(self.erratum.fixed_packages_count, 1)
