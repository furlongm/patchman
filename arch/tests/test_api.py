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


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ArchitectureAPITests(APITestCase):
    """Tests for the Architecture API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser', password='testpass'
        )
        self.client.force_authenticate(user=self.user)

        self.machine_arch = MachineArchitecture.objects.create(name='x86_64')
        self.pkg_arch = PackageArchitecture.objects.create(name='amd64')

    def test_list_machine_architectures(self):
        """Test listing machine architectures."""
        response = self.client.get('/api/machine-architecture/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_machine_architecture(self):
        """Test retrieving a machine architecture."""
        response = self.client.get(f'/api/machine-architecture/{self.machine_arch.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'x86_64')

    def test_list_package_architectures(self):
        """Test listing package architectures."""
        response = self.client.get('/api/package-architecture/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_package_architecture(self):
        """Test retrieving a package architecture."""
        response = self.client.get(f'/api/package-architecture/{self.pkg_arch.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'amd64')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class MachineArchitectureModelTests(TestCase):
    """Tests for the MachineArchitecture model."""

    def test_machine_architecture_creation(self):
        """Test creating a machine architecture."""
        arch = MachineArchitecture.objects.create(name='aarch64')
        self.assertEqual(arch.name, 'aarch64')

    def test_machine_architecture_string_representation(self):
        """Test MachineArchitecture __str__ method."""
        arch = MachineArchitecture.objects.create(name='i686')
        self.assertEqual(str(arch), 'i686')

    def test_machine_architecture_unique_name(self):
        """Test that machine architecture names must be unique."""
        MachineArchitecture.objects.create(name='unique-arch')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            MachineArchitecture.objects.create(name='unique-arch')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class PackageArchitectureModelTests(TestCase):
    """Tests for the PackageArchitecture model."""

    def test_package_architecture_creation(self):
        """Test creating a package architecture."""
        arch = PackageArchitecture.objects.create(name='arm64')
        self.assertEqual(arch.name, 'arm64')

    def test_package_architecture_string_representation(self):
        """Test PackageArchitecture __str__ method."""
        arch = PackageArchitecture.objects.create(name='noarch')
        self.assertEqual(str(arch), 'noarch')

    def test_package_architecture_unique_name(self):
        """Test that package architecture names must be unique."""
        PackageArchitecture.objects.create(name='all')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            PackageArchitecture.objects.create(name='all')

    def test_common_architectures(self):
        """Test creating common architecture types."""
        archs = ['x86_64', 'amd64', 'i386', 'i686', 'noarch', 'all', 'arm64', 'aarch64']
        for arch_name in archs:
            arch = PackageArchitecture.objects.create(name=arch_name)
            self.assertEqual(str(arch), arch_name)
