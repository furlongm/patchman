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

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from arch.models import PackageArchitecture
from packages.models import Package, PackageName, PackageUpdate


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class PackageAPITests(APITestCase):
    """Tests for the Package API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser', password='testpass'
        )
        self.client.force_authenticate(user=self.user)

        self.arch = PackageArchitecture.objects.create(name='amd64')
        self.pkg_name = PackageName.objects.create(name='nginx')
        self.package = Package.objects.create(
            name=self.pkg_name,
            epoch='',
            version='1.18.0',
            release='6ubuntu14',
            arch=self.arch,
            packagetype='D',
        )

    def test_list_packages(self):
        """Test listing all packages."""
        response = self.client.get('/api/package/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_package(self):
        """Test retrieving a single package."""
        response = self.client.get(f'/api/package/{self.package.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['version'], '1.18.0')

    def test_filter_packages_by_name(self):
        """Test filtering packages by name."""
        response = self.client.get('/api/package/', {'name': self.pkg_name.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_packages_by_version(self):
        """Test filtering packages by version."""
        response = self.client.get('/api/package/', {'version': '1.18.0'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_list_package_names(self):
        """Test listing package names."""
        response = self.client.get('/api/package-name/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_package_names(self):
        """Test filtering package names."""
        response = self.client.get('/api/package-name/', {'name': 'nginx'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_package_name(self):
        """Test retrieving a single package name."""
        response = self.client.get(f'/api/package-name/{self.pkg_name.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'nginx')

    def test_list_package_updates(self):
        """Test listing package updates."""
        response = self.client.get('/api/package-update/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_package_update(self):
        """Test retrieving a single package update."""
        from packages.models import PackageUpdate
        new_pkg = Package.objects.create(
            name=self.pkg_name,
            arch=self.arch,
            epoch='',
            version='1.20.0',
            release='1',
            packagetype='D',
        )
        update = PackageUpdate.objects.create(
            oldpackage=self.package,
            newpackage=new_pkg,
            security=True,
        )
        response = self.client.get(f'/api/package-update/{update.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['security'])


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class PackageModelTests(TestCase):
    """Tests for the Package model."""

    def setUp(self):
        """Set up test data."""
        self.arch = PackageArchitecture.objects.create(name='amd64')
        self.pkg_name = PackageName.objects.create(name='nginx')

    def test_package_creation(self):
        """Test creating a package with all fields."""
        package = Package.objects.create(
            name=self.pkg_name,
            epoch='1',
            version='1.18.0',
            release='6ubuntu14',
            arch=self.arch,
            packagetype='D',
        )
        self.assertEqual(package.version, '1.18.0')
        self.assertEqual(package.packagetype, 'D')

    def test_package_string_representation(self):
        """Test Package __str__ method."""
        package = Package.objects.create(
            name=self.pkg_name,
            version='1.18.0',
            release='6ubuntu14',
            arch=self.arch,
            packagetype='D',
        )
        str_rep = str(package)
        self.assertIn('nginx', str_rep)
        self.assertIn('1.18.0', str_rep)

    def test_package_type_choices(self):
        """Test package type constants."""
        self.assertEqual(Package.RPM, 'R')
        self.assertEqual(Package.DEB, 'D')
        self.assertEqual(Package.ARCH, 'A')
        self.assertEqual(Package.GENTOO, 'G')
        self.assertEqual(Package.UNKNOWN, 'U')

    def test_package_with_epoch(self):
        """Test package with epoch field."""
        package = Package.objects.create(
            name=self.pkg_name,
            epoch='2',
            version='1.18.0',
            release='1',
            arch=self.arch,
            packagetype='R',
        )
        self.assertEqual(package.epoch, '2')

    def test_package_without_release(self):
        """Test package without release field (Debian style)."""
        package = Package.objects.create(
            name=self.pkg_name,
            version='1.18.0-6ubuntu14',
            arch=self.arch,
            packagetype='D',
        )
        self.assertIsNone(package.release)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class PackageNameModelTests(TestCase):
    """Tests for the PackageName model."""

    def test_package_name_creation(self):
        """Test creating a package name."""
        pkg_name = PackageName.objects.create(name='curl')
        self.assertEqual(pkg_name.name, 'curl')

    def test_package_name_string_representation(self):
        """Test PackageName __str__ method."""
        pkg_name = PackageName.objects.create(name='openssl')
        self.assertEqual(str(pkg_name), 'openssl')

    def test_package_name_unique(self):
        """Test that package names must be unique."""
        PackageName.objects.create(name='unique-package')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            PackageName.objects.create(name='unique-package')

    def test_package_name_get_absolute_url(self):
        """Test PackageName.get_absolute_url()."""
        pkg_name = PackageName.objects.create(name='testpkg')
        url = pkg_name.get_absolute_url()
        self.assertIn('testpkg', url)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class PackageUpdateModelTests(TestCase):
    """Tests for the PackageUpdate model."""

    def setUp(self):
        """Set up test data."""
        self.arch = PackageArchitecture.objects.create(name='amd64')
        self.pkg_name = PackageName.objects.create(name='openssl')
        self.old_package = Package.objects.create(
            name=self.pkg_name,
            version='3.0.2',
            release='0ubuntu1.12',
            arch=self.arch,
            packagetype='D',
        )
        self.new_package = Package.objects.create(
            name=self.pkg_name,
            version='3.0.2',
            release='0ubuntu1.13',
            arch=self.arch,
            packagetype='D',
        )

    def test_package_update_creation(self):
        """Test creating a package update."""
        update = PackageUpdate.objects.create(
            oldpackage=self.old_package,
            newpackage=self.new_package,
            security=True,
        )
        self.assertEqual(update.oldpackage, self.old_package)
        self.assertEqual(update.newpackage, self.new_package)
        self.assertTrue(update.security)

    def test_package_update_security_flag(self):
        """Test security vs bugfix classification."""
        security_update = PackageUpdate.objects.create(
            oldpackage=self.old_package,
            newpackage=self.new_package,
            security=True,
        )
        self.assertTrue(security_update.security)

        bugfix_update = PackageUpdate.objects.create(
            oldpackage=self.old_package,
            newpackage=self.new_package,
            security=False,
        )
        self.assertFalse(bugfix_update.security)

    def test_package_update_api(self):
        """Test PackageUpdate API endpoint."""
        PackageUpdate.objects.create(
            oldpackage=self.old_package,
            newpackage=self.new_package,
            security=True,
        )
        user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_login(user)

        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=user)

        response = api_client.get('/api/package-update/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_package_updates_by_security(self):
        """Test filtering package updates by security flag."""
        PackageUpdate.objects.create(
            oldpackage=self.old_package,
            newpackage=self.new_package,
            security=True,
        )
        user = User.objects.create_user(username='testuser', password='testpass')
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=user)

        response = api_client.get('/api/package-update/', {'security': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
