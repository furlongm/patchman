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
from packages.models import Package, PackageName, PackageUpdate


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class PackageMethodTests(TestCase):
    """Tests for Package model methods."""

    def setUp(self):
        """Set up test data."""
        self.arch = PackageArchitecture.objects.create(name='amd64')
        self.pkg_name = PackageName.objects.create(name='nginx')

    def test_get_version_string_deb(self):
        """Test get_version_string() for deb packages."""
        pkg = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='', version='1.18.0', release='6ubuntu14', packagetype='D'
        )
        self.assertEqual(pkg.get_version_string(), '1.18.0-6ubuntu14')

    def test_get_version_string_deb_with_epoch(self):
        """Test get_version_string() for deb packages with epoch."""
        pkg = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='1', version='1.18.0', release='6ubuntu14', packagetype='D'
        )
        self.assertEqual(pkg.get_version_string(), '1:1.18.0-6ubuntu14')

    def test_get_version_string_deb_no_release(self):
        """Test get_version_string() for deb packages without release."""
        pkg = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='', version='1.18.0', release='', packagetype='D'
        )
        self.assertEqual(pkg.get_version_string(), '1.18.0')

    def test_get_version_string_rpm(self):
        """Test get_version_string() for rpm packages."""
        pkg = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='0', version='1.18.0', release='1.el9', packagetype='R'
        )
        version_tuple = pkg.get_version_string()
        self.assertEqual(version_tuple, ('0', '1.18.0', '1.el9'))

    def test_compare_version_deb_equal(self):
        """Test compare_version() for equal deb packages."""
        pkg1 = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='', version='1.18.0', release='1', packagetype='D'
        )
        pkg_name2 = PackageName.objects.create(name='nginx2')
        pkg2 = Package.objects.create(
            name=pkg_name2, arch=self.arch,
            epoch='', version='1.18.0', release='1', packagetype='D'
        )
        self.assertEqual(pkg1.compare_version(pkg2), 0)

    def test_compare_version_deb_greater(self):
        """Test compare_version() for newer deb package."""
        pkg1 = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='', version='1.20.0', release='1', packagetype='D'
        )
        pkg_name2 = PackageName.objects.create(name='nginx-old')
        pkg2 = Package.objects.create(
            name=pkg_name2, arch=self.arch,
            epoch='', version='1.18.0', release='1', packagetype='D'
        )
        self.assertEqual(pkg1.compare_version(pkg2), 1)

    def test_compare_version_deb_lesser(self):
        """Test compare_version() for older deb package."""
        pkg1 = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='', version='1.16.0', release='1', packagetype='D'
        )
        pkg_name2 = PackageName.objects.create(name='nginx-new')
        pkg2 = Package.objects.create(
            name=pkg_name2, arch=self.arch,
            epoch='', version='1.18.0', release='1', packagetype='D'
        )
        self.assertEqual(pkg1.compare_version(pkg2), -1)

    def test_str_deb_package(self):
        """Test __str__ for deb package."""
        pkg = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='', version='1.18.0', release='6ubuntu14', packagetype='D'
        )
        self.assertEqual(str(pkg), 'nginx_1.18.0-6ubuntu14_amd64.deb')

    def test_str_deb_package_with_epoch(self):
        """Test __str__ for deb package with epoch."""
        pkg = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='1', version='1.18.0', release='6ubuntu14', packagetype='D'
        )
        self.assertEqual(str(pkg), 'nginx_1:1.18.0-6ubuntu14_amd64.deb')

    def test_str_rpm_package(self):
        """Test __str__ for rpm package."""
        pkg = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='', version='1.18.0', release='1.el9', packagetype='R'
        )
        self.assertEqual(str(pkg), 'nginx-1.18.0-1.el9-amd64.rpm')

    def test_package_equality(self):
        """Test Package __eq__ method."""
        pkg1 = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='', version='1.18.0', release='1', packagetype='D'
        )
        # Same attributes = equal
        self.assertEqual(pkg1, pkg1)

    def test_package_inequality(self):
        """Test Package __ne__ method."""
        pkg1 = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='', version='1.18.0', release='1', packagetype='D'
        )
        pkg_name2 = PackageName.objects.create(name='curl')
        pkg2 = Package.objects.create(
            name=pkg_name2, arch=self.arch,
            epoch='', version='7.81.0', release='1', packagetype='D'
        )
        self.assertNotEqual(pkg1, pkg2)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class PackageUpdateMethodTests(TestCase):
    """Tests for PackageUpdate model."""

    def setUp(self):
        """Set up test data."""
        self.arch = PackageArchitecture.objects.create(name='amd64')
        self.pkg_name = PackageName.objects.create(name='openssl')
        self.old_pkg = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='', version='3.0.0', release='1', packagetype='D'
        )
        self.new_pkg = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='', version='3.0.1', release='1', packagetype='D'
        )

    def test_package_update_str(self):
        """Test PackageUpdate __str__ method."""
        update = PackageUpdate.objects.create(
            oldpackage=self.old_pkg,
            newpackage=self.new_pkg,
            security=True,
        )
        str_repr = str(update)
        self.assertIn('openssl', str_repr)

    def test_package_update_security_flag(self):
        """Test PackageUpdate security flag."""
        sec_update = PackageUpdate.objects.create(
            oldpackage=self.old_pkg,
            newpackage=self.new_pkg,
            security=True,
        )
        self.assertTrue(sec_update.security)

        bug_pkg = Package.objects.create(
            name=self.pkg_name, arch=self.arch,
            epoch='', version='3.0.2', release='1', packagetype='D'
        )
        bug_update = PackageUpdate.objects.create(
            oldpackage=self.old_pkg,
            newpackage=bug_pkg,
            security=False,
        )
        self.assertFalse(bug_update.security)
