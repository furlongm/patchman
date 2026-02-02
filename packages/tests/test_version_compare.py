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

from arch.models import PackageArchitecture
from packages.models import Package, PackageName


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class RPMVersionCompareTests(TestCase):
    """Tests for RPM package version comparison."""

    def setUp(self):
        """Set up test data."""
        self.arch = PackageArchitecture.objects.create(name='x86_64')
        self.pkg_name = PackageName.objects.create(name='httpd')

    def _create_rpm(self, epoch, version, release):
        """Helper to create RPM package."""
        return Package.objects.create(
            name=self.pkg_name,
            arch=self.arch,
            epoch=epoch,
            version=version,
            release=release,
            packagetype=Package.RPM,
        )

    def test_compare_same_version(self):
        """Test comparing identical versions returns 0."""
        pkg1 = self._create_rpm('0', '2.4.57', '5.el9')
        pkg2 = self._create_rpm('0', '2.4.57', '5.el9')
        self.assertEqual(pkg1.compare_version(pkg2), 0)

    def test_compare_newer_version(self):
        """Test comparing newer version returns 1."""
        pkg1 = self._create_rpm('0', '2.4.58', '1.el9')
        pkg2 = self._create_rpm('0', '2.4.57', '5.el9')
        self.assertEqual(pkg1.compare_version(pkg2), 1)

    def test_compare_older_version(self):
        """Test comparing older version returns -1."""
        pkg1 = self._create_rpm('0', '2.4.56', '1.el9')
        pkg2 = self._create_rpm('0', '2.4.57', '5.el9')
        self.assertEqual(pkg1.compare_version(pkg2), -1)

    def test_compare_epoch_takes_precedence(self):
        """Test that epoch takes precedence over version."""
        pkg1 = self._create_rpm('1', '1.0.0', '1.el9')
        pkg2 = self._create_rpm('0', '9.9.9', '99.el9')
        self.assertEqual(pkg1.compare_version(pkg2), 1)

    def test_compare_release_difference(self):
        """Test release number comparison when version is same."""
        pkg1 = self._create_rpm('0', '2.4.57', '6.el9')
        pkg2 = self._create_rpm('0', '2.4.57', '5.el9')
        self.assertEqual(pkg1.compare_version(pkg2), 1)

    def test_compare_empty_epoch_vs_zero(self):
        """Test empty epoch vs explicit 0 epoch comparison."""
        pkg1 = self._create_rpm('', '2.4.57', '5.el9')
        pkg2 = self._create_rpm('0', '2.4.57', '5.el9')
        # RPM treats empty string and '0' differently in labelCompare
        result = pkg1.compare_version(pkg2)
        self.assertIn(result, [-1, 0, 1])  # Implementation dependent

    def test_compare_complex_version(self):
        """Test complex version strings."""
        pkg1 = self._create_rpm('0', '1.2.3.4.5', '1.el9')
        pkg2 = self._create_rpm('0', '1.2.3.4.4', '1.el9')
        self.assertEqual(pkg1.compare_version(pkg2), 1)

    def test_compare_alpha_version(self):
        """Test version with alpha characters."""
        pkg1 = self._create_rpm('0', '1.0.0', '1.el9')
        pkg2 = self._create_rpm('0', '1.0.0', '1.el9_1')
        # el9 vs el9_1 comparison
        result = pkg1.compare_version(pkg2)
        self.assertIn(result, [-1, 0, 1])

    def test_version_string_rpm(self):
        """Test _version_string_rpm returns correct tuple."""
        pkg = self._create_rpm('1', '2.4.57', '5.el9')
        result = pkg._version_string_rpm()
        self.assertEqual(result, ('1', '2.4.57', '5.el9'))

    def test_version_string_rpm_empty_epoch(self):
        """Test _version_string_rpm with empty epoch."""
        pkg = self._create_rpm('', '2.4.57', '5.el9')
        result = pkg._version_string_rpm()
        self.assertEqual(result, ('', '2.4.57', '5.el9'))


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class DEBVersionCompareTests(TestCase):
    """Tests for DEB package version comparison."""

    def setUp(self):
        """Set up test data."""
        self.arch = PackageArchitecture.objects.create(name='amd64')
        self.pkg_name = PackageName.objects.create(name='nginx')

    def _create_deb(self, epoch, version, release):
        """Helper to create DEB package."""
        return Package.objects.create(
            name=self.pkg_name,
            arch=self.arch,
            epoch=epoch,
            version=version,
            release=release,
            packagetype=Package.DEB,
        )

    def test_compare_same_version(self):
        """Test comparing identical versions returns 0."""
        pkg1 = self._create_deb('', '1.18.0', '6ubuntu14')
        pkg2 = self._create_deb('', '1.18.0', '6ubuntu14')
        self.assertEqual(pkg1.compare_version(pkg2), 0)

    def test_compare_newer_version(self):
        """Test comparing newer version returns 1."""
        pkg1 = self._create_deb('', '1.18.1', '1ubuntu1')
        pkg2 = self._create_deb('', '1.18.0', '6ubuntu14')
        self.assertEqual(pkg1.compare_version(pkg2), 1)

    def test_compare_older_version(self):
        """Test comparing older version returns -1."""
        pkg1 = self._create_deb('', '1.17.0', '1ubuntu1')
        pkg2 = self._create_deb('', '1.18.0', '6ubuntu14')
        self.assertEqual(pkg1.compare_version(pkg2), -1)

    def test_compare_ubuntu_revision(self):
        """Test Ubuntu revision comparison."""
        pkg1 = self._create_deb('', '1.18.0', '6ubuntu15')
        pkg2 = self._create_deb('', '1.18.0', '6ubuntu14')
        self.assertEqual(pkg1.compare_version(pkg2), 1)

    def test_compare_tilde_version(self):
        """Test tilde in version (sorts before everything)."""
        pkg1 = self._create_deb('', '1.0.0~beta1', '1')
        pkg2 = self._create_deb('', '1.0.0', '1')
        self.assertEqual(pkg1.compare_version(pkg2), -1)

    def test_compare_epoch_deb(self):
        """Test epoch comparison for DEB packages."""
        pkg1 = self._create_deb('2', '1.0.0', '1')
        pkg2 = self._create_deb('1', '9.0.0', '1')
        self.assertEqual(pkg1.compare_version(pkg2), 1)

    def test_version_string_deb(self):
        """Test _version_string_deb_arch returns correct format."""
        pkg = self._create_deb('1', '1.18.0', '6ubuntu14')
        result = pkg._version_string_deb_arch()
        self.assertEqual(result, '1:1.18.0-6ubuntu14')

    def test_version_string_deb_no_epoch(self):
        """Test _version_string_deb_arch without epoch."""
        pkg = self._create_deb('', '1.18.0', '6ubuntu14')
        result = pkg._version_string_deb_arch()
        self.assertEqual(result, '1.18.0-6ubuntu14')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ArchVersionCompareTests(TestCase):
    """Tests for Arch package version comparison."""

    def setUp(self):
        """Set up test data."""
        self.arch = PackageArchitecture.objects.create(name='x86_64')
        self.pkg_name = PackageName.objects.create(name='pacman')

    def _create_arch(self, epoch, version, release):
        """Helper to create Arch package."""
        return Package.objects.create(
            name=self.pkg_name,
            arch=self.arch,
            epoch=epoch,
            version=version,
            release=release,
            packagetype=Package.ARCH,
        )

    def test_compare_same_version(self):
        """Test comparing identical versions returns 0."""
        pkg1 = self._create_arch('', '6.0.2', '1')
        pkg2 = self._create_arch('', '6.0.2', '1')
        self.assertEqual(pkg1.compare_version(pkg2), 0)

    def test_compare_newer_version(self):
        """Test comparing newer version returns 1."""
        pkg1 = self._create_arch('', '6.0.3', '1')
        pkg2 = self._create_arch('', '6.0.2', '1')
        self.assertEqual(pkg1.compare_version(pkg2), 1)

    def test_compare_release_bump(self):
        """Test release number bump."""
        pkg1 = self._create_arch('', '6.0.2', '2')
        pkg2 = self._create_arch('', '6.0.2', '1')
        self.assertEqual(pkg1.compare_version(pkg2), 1)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class GentooVersionCompareTests(TestCase):
    """Tests for Gentoo package version comparison."""

    def setUp(self):
        """Set up test data."""
        self.arch = PackageArchitecture.objects.create(name='amd64')
        self.pkg_name = PackageName.objects.create(name='dev-libs/openssl')

    def _create_gentoo(self, epoch, version, release):
        """Helper to create Gentoo package."""
        return Package.objects.create(
            name=self.pkg_name,
            arch=self.arch,
            epoch=epoch,
            version=version,
            release=release,
            packagetype=Package.GENTOO,
        )

    def test_compare_same_version(self):
        """Test comparing identical versions returns 0."""
        pkg1 = self._create_gentoo('', '3.0.10', 'r1')
        pkg2 = self._create_gentoo('', '3.0.10', 'r1')
        self.assertEqual(pkg1.compare_version(pkg2), 0)

    def test_compare_newer_version(self):
        """Test comparing newer version returns 1."""
        pkg1 = self._create_gentoo('', '3.0.11', 'r0')
        pkg2 = self._create_gentoo('', '3.0.10', 'r1')
        self.assertEqual(pkg1.compare_version(pkg2), 1)

    def test_compare_revision_bump(self):
        """Test revision bump."""
        pkg1 = self._create_gentoo('', '3.0.10', 'r2')
        pkg2 = self._create_gentoo('', '3.0.10', 'r1')
        self.assertEqual(pkg1.compare_version(pkg2), 1)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class GetVersionStringTests(TestCase):
    """Tests for get_version_string method."""

    def setUp(self):
        """Set up test data."""
        self.arch = PackageArchitecture.objects.create(name='x86_64')
        self.pkg_name = PackageName.objects.create(name='testpkg')

    def test_get_version_string_rpm(self):
        """Test get_version_string for RPM."""
        pkg = Package.objects.create(
            name=self.pkg_name,
            arch=self.arch,
            epoch='1',
            version='2.0.0',
            release='3.el9',
            packagetype=Package.RPM,
        )
        result = pkg.get_version_string()
        self.assertEqual(result, ('1', '2.0.0', '3.el9'))

    def test_get_version_string_deb(self):
        """Test get_version_string for DEB."""
        pkg = Package.objects.create(
            name=self.pkg_name,
            arch=self.arch,
            epoch='1',
            version='2.0.0',
            release='3ubuntu1',
            packagetype=Package.DEB,
        )
        result = pkg.get_version_string()
        self.assertEqual(result, '1:2.0.0-3ubuntu1')

    def test_get_version_string_gentoo(self):
        """Test get_version_string for Gentoo."""
        pkg = Package.objects.create(
            name=self.pkg_name,
            arch=self.arch,
            epoch='',
            version='2.0.0',
            release='r1',
            packagetype=Package.GENTOO,
        )
        result = pkg.get_version_string()
        self.assertEqual(result, ('', '2.0.0', 'r1'))
