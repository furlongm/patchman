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

from arch.models import MachineArchitecture, PackageArchitecture
from packages.models import Package, PackageName
from repos.models import Mirror, MirrorPackage, Repository


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class RepositoryAPITests(APITestCase):
    """Tests for the Repository API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser', password='testpass'
        )
        self.client.force_authenticate(user=self.user)

        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.repo = Repository.objects.create(
            name='ubuntu-main',
            arch=self.arch,
            repotype='D',
            enabled=True,
        )

    def test_list_repos(self):
        """Test listing all repositories."""
        response = self.client.get('/api/repo/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_repo(self):
        """Test retrieving a single repository."""
        response = self.client.get(f'/api/repo/{self.repo.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'ubuntu-main')

    def test_list_mirrors(self):
        """Test listing mirrors."""
        Mirror.objects.create(
            repo=self.repo,
            url='http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64',
        )
        response = self.client.get('/api/mirror/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_mirror(self):
        """Test retrieving a single mirror."""
        mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64',
        )
        response = self.client.get(f'/api/mirror/{mirror.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('archive.ubuntu.com', response.data['url'])

    def test_list_mirror_packages(self):
        """Test listing mirror packages."""
        response = self.client.get('/api/mirror-package/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_mirror_package(self):
        """Test retrieving a single mirror package."""
        from arch.models import PackageArchitecture
        from packages.models import Package, PackageName
        pkg_arch = PackageArchitecture.objects.create(name='amd64')
        pkg_name = PackageName.objects.create(name='nginx')
        package = Package.objects.create(
            name=pkg_name,
            arch=pkg_arch,
            epoch='',
            version='1.18.0',
            release='1',
            packagetype='D',
        )
        mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64',
        )
        mirror_package = MirrorPackage.objects.create(
            mirror=mirror,
            package=package,
        )
        response = self.client.get(f'/api/mirror-package/{mirror_package.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class RepositoryModelTests(TestCase):
    """Tests for the Repository model."""

    def setUp(self):
        """Set up test data."""
        self.arch = MachineArchitecture.objects.create(name='x86_64')

    def test_repository_creation(self):
        """Test creating a repository."""
        repo = Repository.objects.create(
            name='test-repo',
            arch=self.arch,
            repotype='R',
            enabled=True,
        )
        self.assertEqual(repo.name, 'test-repo')
        self.assertEqual(repo.repotype, 'R')

    def test_repository_string_representation(self):
        """Test Repository __str__ method."""
        repo = Repository.objects.create(
            name='ubuntu-security',
            arch=self.arch,
            repotype='D',
        )
        self.assertEqual(str(repo), 'ubuntu-security')

    def test_repository_type_choices(self):
        """Test repository type constants."""
        self.assertEqual(Repository.RPM, 'R')
        self.assertEqual(Repository.DEB, 'D')
        self.assertEqual(Repository.ARCH, 'A')
        self.assertEqual(Repository.GENTOO, 'G')

    def test_repository_unique_name(self):
        """Test that repository names must be unique."""
        Repository.objects.create(
            name='unique-repo',
            arch=self.arch,
            repotype='D',
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Repository.objects.create(
                name='unique-repo',
                arch=self.arch,
                repotype='D',
            )

    def test_repository_security_flag(self):
        """Test repository security flag."""
        security_repo = Repository.objects.create(
            name='ubuntu-security',
            arch=self.arch,
            repotype='D',
            security=True,
        )
        self.assertTrue(security_repo.security)

        normal_repo = Repository.objects.create(
            name='ubuntu-main',
            arch=self.arch,
            repotype='D',
            security=False,
        )
        self.assertFalse(normal_repo.security)

    def test_repository_enabled_default(self):
        """Test that repository enabled defaults to True."""
        repo = Repository.objects.create(
            name='test-repo',
            arch=self.arch,
            repotype='D',
        )
        self.assertTrue(repo.enabled)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class MirrorModelTests(TestCase):
    """Tests for the Mirror model."""

    def setUp(self):
        """Set up test data."""
        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.repo = Repository.objects.create(
            name='test-repo',
            arch=self.arch,
            repotype='D',
        )

    def test_mirror_creation(self):
        """Test creating a mirror."""
        mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64',
        )
        self.assertEqual(mirror.repo, self.repo)
        self.assertIn('archive.ubuntu.com', mirror.url)

    def test_mirror_string_representation(self):
        """Test Mirror __str__ method."""
        mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64',
        )
        str_rep = str(mirror)
        self.assertIn('archive.ubuntu.com', str_rep)

    def test_mirror_enabled_default(self):
        """Test that mirror enabled defaults to True."""
        mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://example.com/repo',
        )
        self.assertTrue(mirror.enabled)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class MirrorPackageModelTests(TestCase):
    """Tests for the MirrorPackage model."""

    def setUp(self):
        """Set up test data."""
        self.machine_arch = MachineArchitecture.objects.create(name='x86_64')
        self.pkg_arch = PackageArchitecture.objects.create(name='amd64')
        self.repo = Repository.objects.create(
            name='test-repo',
            arch=self.machine_arch,
            repotype='D',
        )
        self.mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://example.com/repo',
        )
        self.pkg_name = PackageName.objects.create(name='nginx')
        self.package = Package.objects.create(
            name=self.pkg_name,
            version='1.18.0',
            release='6ubuntu14',
            arch=self.pkg_arch,
            packagetype='D',
        )

    def test_mirror_package_creation(self):
        """Test creating a mirror package link."""
        mp = MirrorPackage.objects.create(
            mirror=self.mirror,
            package=self.package,
        )
        self.assertEqual(mp.mirror, self.mirror)
        self.assertEqual(mp.package, self.package)

    def test_mirror_packages_relationship(self):
        """Test Mirror.packages ManyToMany relationship."""
        MirrorPackage.objects.create(
            mirror=self.mirror,
            package=self.package,
        )
        self.assertIn(self.package, self.mirror.packages.all())

    def test_mirror_package_api(self):
        """Test MirrorPackage API endpoint."""
        MirrorPackage.objects.create(
            mirror=self.mirror,
            package=self.package,
        )
        user = User.objects.create_user(username='testuser', password='testpass')
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=user)

        response = api_client.get('/api/mirror-package/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
