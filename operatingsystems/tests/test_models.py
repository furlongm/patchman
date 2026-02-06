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

from operatingsystems.models import OSRelease, OSVariant
from operatingsystems.utils import normalize_el_osrelease


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class NormalizeELOSReleaseTests(TestCase):
    """Tests for normalize_el_osrelease() function.

    This function normalizes EL-based distro names to major version only,
    ensuring consistent OSRelease naming across errata and reports.

    Regression notes - OLD behavior that caused duplicate OSReleases:
    - 'rocky-linux-10.1' -> 'Rocky Linux 10.1' (should be 'Rocky Linux 10')
    - 'almalinux-10.1' -> 'Alma Linux 10.1' (should be 'Alma Linux 10')
    - 'Rocky Linux 10.1' -> passed through unchanged (should be 'Rocky Linux 10')
    - 'CentOS 7.9' -> passed through unchanged (should be 'CentOS 7')
    """

    # ===========================================
    # REGRESSION TESTS - These were bugs before
    # ===========================================

    def test_regression_rocky_dash_format_minor_stripped(self):
        """REGRESSION: rocky-linux-10.1 was creating 'Rocky Linux 10.1'

        Old behavior: version = osrelease_name.split('-')[2] -> '10.1'
                      result = 'Rocky Linux 10.1'
        New behavior: major_version = '10.1'.split('.')[0] -> '10'
                      result = 'Rocky Linux 10'
        """
        # OLD (wrong): 'Rocky Linux 10.1'
        # NEW (correct): 'Rocky Linux 10'
        self.assertEqual(normalize_el_osrelease('rocky-linux-10.1'), 'Rocky Linux 10')
        self.assertNotEqual(normalize_el_osrelease('rocky-linux-10.1'), 'Rocky Linux 10.1')

    def test_regression_alma_dash_format_minor_stripped(self):
        """REGRESSION: almalinux-10.1 was creating 'Alma Linux 10.1'

        Old behavior: version = osrelease_name.split('-')[1] -> '10.1'
                      result = 'Alma Linux 10.1'
        New behavior: major_version = '10.1'.split('.')[0] -> '10'
                      result = 'Alma Linux 10'
        """
        # OLD (wrong): 'Alma Linux 10.1'
        # NEW (correct): 'Alma Linux 10'
        self.assertEqual(normalize_el_osrelease('almalinux-10.1'), 'Alma Linux 10')
        self.assertNotEqual(normalize_el_osrelease('almalinux-10.1'), 'Alma Linux 10.1')

    def test_regression_rocky_human_format_minor_stripped(self):
        """REGRESSION: 'Rocky Linux 10.1' was passed through unchanged

        Old behavior: no handling, passed through as 'Rocky Linux 10.1'
        New behavior: normalized to 'Rocky Linux 10'
        """
        # OLD (wrong): 'Rocky Linux 10.1'
        # NEW (correct): 'Rocky Linux 10'
        self.assertEqual(normalize_el_osrelease('Rocky Linux 10.1'), 'Rocky Linux 10')
        self.assertNotEqual(normalize_el_osrelease('Rocky Linux 10.1'), 'Rocky Linux 10.1')

    def test_regression_centos_minor_stripped(self):
        """REGRESSION: 'CentOS 7.9' was passed through unchanged

        Old behavior: no handling for human-readable format
        New behavior: normalized to 'CentOS 7'
        """
        # OLD (wrong): 'CentOS 7.9'
        # NEW (correct): 'CentOS 7'
        self.assertEqual(normalize_el_osrelease('CentOS 7.9'), 'CentOS 7')
        self.assertNotEqual(normalize_el_osrelease('CentOS 7.9'), 'CentOS 7.9')

    # ===========================================
    # STANDARD TESTS - Expected behavior
    # ===========================================

    def test_rocky_linux_with_minor_version(self):
        """Test Rocky Linux X.Y -> Rocky Linux X"""
        self.assertEqual(normalize_el_osrelease('Rocky Linux 10.1'), 'Rocky Linux 10')
        self.assertEqual(normalize_el_osrelease('Rocky Linux 9.3'), 'Rocky Linux 9')

    def test_rocky_linux_dash_format(self):
        """Test rocky-linux-X.Y -> Rocky Linux X"""
        self.assertEqual(normalize_el_osrelease('rocky-linux-10.1'), 'Rocky Linux 10')
        self.assertEqual(normalize_el_osrelease('rocky-linux-9.3'), 'Rocky Linux 9')

    def test_alma_linux_with_minor_version(self):
        """Test Alma Linux X.Y -> Alma Linux X"""
        self.assertEqual(normalize_el_osrelease('Alma Linux 10.1'), 'Alma Linux 10')
        self.assertEqual(normalize_el_osrelease('Alma Linux 9.3'), 'Alma Linux 9')

    def test_almalinux_dash_format(self):
        """Test almalinux-X.Y -> Alma Linux X"""
        self.assertEqual(normalize_el_osrelease('almalinux-10.1'), 'Alma Linux 10')
        self.assertEqual(normalize_el_osrelease('almalinux-9.3'), 'Alma Linux 9')

    def test_almalinux_no_space(self):
        """Test AlmaLinux X.Y -> AlmaLinux X"""
        self.assertEqual(normalize_el_osrelease('AlmaLinux 10.1'), 'AlmaLinux 10')

    def test_centos_with_minor_version(self):
        """Test CentOS X.Y -> CentOS X"""
        self.assertEqual(normalize_el_osrelease('CentOS 7.9'), 'CentOS 7')
        self.assertEqual(normalize_el_osrelease('CentOS 8.5'), 'CentOS 8')

    def test_rhel_with_minor_version(self):
        """Test RHEL X.Y -> RHEL X"""
        self.assertEqual(normalize_el_osrelease('RHEL 8.2'), 'RHEL 8')
        self.assertEqual(normalize_el_osrelease('RHEL 9.1'), 'RHEL 9')

    def test_red_hat_enterprise_linux_with_minor_version(self):
        """Test Red Hat Enterprise Linux X.Y -> Red Hat Enterprise Linux X"""
        self.assertEqual(
            normalize_el_osrelease('Red Hat Enterprise Linux 8.2'),
            'Red Hat Enterprise Linux 8'
        )

    def test_oracle_linux_with_minor_version(self):
        """Test Oracle Linux X.Y -> Oracle Linux X"""
        self.assertEqual(normalize_el_osrelease('Oracle Linux 8.1'), 'Oracle Linux 8')

    def test_amazon_linux_normalization(self):
        """Test Amazon Linux -> Amazon Linux 1"""
        self.assertEqual(normalize_el_osrelease('Amazon Linux'), 'Amazon Linux 1')
        self.assertEqual(normalize_el_osrelease('Amazon Linux AMI'), 'Amazon Linux 1')

    # ===========================================
    # NO-OP TESTS - Should remain unchanged
    # ===========================================

    def test_major_version_only_unchanged(self):
        """Test that major-version-only names are unchanged (no regression)"""
        self.assertEqual(normalize_el_osrelease('Rocky Linux 10'), 'Rocky Linux 10')
        self.assertEqual(normalize_el_osrelease('CentOS 7'), 'CentOS 7')
        self.assertEqual(normalize_el_osrelease('RHEL 9'), 'RHEL 9')
        self.assertEqual(normalize_el_osrelease('Alma Linux 9'), 'Alma Linux 9')

    def test_non_el_distros_unchanged(self):
        """Test that non-EL distros are unchanged (no false positives)"""
        self.assertEqual(normalize_el_osrelease('Ubuntu 22.04'), 'Ubuntu 22.04')
        self.assertEqual(normalize_el_osrelease('Debian 12'), 'Debian 12')
        self.assertEqual(normalize_el_osrelease('Fedora 39'), 'Fedora 39')
        self.assertEqual(normalize_el_osrelease('Arch Linux'), 'Arch Linux')
        self.assertEqual(normalize_el_osrelease('openSUSE Leap 15.5'), 'openSUSE Leap 15.5')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class OSReleaseMethodTests(TestCase):
    """Tests for OSRelease model methods."""

    def test_osrelease_creation(self):
        """Test creating an OSRelease."""
        release = OSRelease.objects.create(name='Ubuntu 22.04')
        self.assertEqual(release.name, 'Ubuntu 22.04')

    def test_osrelease_str(self):
        """Test OSRelease __str__ method."""
        release = OSRelease.objects.create(name='Ubuntu 22.04')
        self.assertEqual(str(release), 'Ubuntu 22.04')

    def test_osrelease_get_absolute_url(self):
        """Test OSRelease.get_absolute_url()."""
        release = OSRelease.objects.create(name='Rocky Linux 9')
        url = release.get_absolute_url()
        self.assertIn(str(release.id), url)

    def test_osrelease_unique_name(self):
        """Test OSRelease name is unique."""
        OSRelease.objects.create(name='Ubuntu 22.04')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            OSRelease.objects.create(name='Ubuntu 22.04')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class OSVariantMethodTests(TestCase):
    """Tests for OSVariant model methods."""

    def setUp(self):
        """Set up test data."""
        self.release = OSRelease.objects.create(name='Ubuntu 22.04')

    def test_osvariant_creation(self):
        """Test creating an OSVariant."""
        variant = OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS',
            osrelease=self.release,
        )
        self.assertEqual(variant.name, 'Ubuntu 22.04.3 LTS')
        self.assertEqual(variant.osrelease, self.release)

    def test_osvariant_str(self):
        """Test OSVariant __str__ method."""
        variant = OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS',
            osrelease=self.release,
        )
        # __str__ returns 'name arch' format
        self.assertIn('Ubuntu 22.04.3 LTS', str(variant))

    def test_osvariant_get_absolute_url(self):
        """Test OSVariant.get_absolute_url()."""
        variant = OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS',
            osrelease=self.release,
        )
        url = variant.get_absolute_url()
        self.assertIn(str(variant.id), url)

    def test_osvariant_unique_name(self):
        """Test OSVariant name is unique."""
        OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS',
            osrelease=self.release,
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            OSVariant.objects.create(
                name='Ubuntu 22.04.3 LTS',
                osrelease=self.release,
            )
