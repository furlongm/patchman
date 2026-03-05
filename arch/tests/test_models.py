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

from arch.models import MachineArchitecture, PackageArchitecture


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class MachineArchitectureMethodTests(TestCase):
    """Tests for MachineArchitecture model methods."""

    def test_machine_arch_creation(self):
        """Test creating a MachineArchitecture."""
        arch = MachineArchitecture.objects.create(name='x86_64')
        self.assertEqual(arch.name, 'x86_64')

    def test_machine_arch_str(self):
        """Test MachineArchitecture __str__ method."""
        arch = MachineArchitecture.objects.create(name='x86_64')
        self.assertEqual(str(arch), 'x86_64')

    def test_machine_arch_unique_name(self):
        """Test MachineArchitecture name is unique."""
        MachineArchitecture.objects.create(name='x86_64')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            MachineArchitecture.objects.create(name='x86_64')

    def test_common_machine_architectures(self):
        """Test common machine architecture values."""
        archs = ['x86_64', 'aarch64', 'i686', 'armv7l', 'ppc64le']
        for name in archs:
            arch = MachineArchitecture.objects.create(name=name)
            self.assertEqual(str(arch), name)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class PackageArchitectureMethodTests(TestCase):
    """Tests for PackageArchitecture model methods."""

    def test_package_arch_creation(self):
        """Test creating a PackageArchitecture."""
        arch = PackageArchitecture.objects.create(name='amd64')
        self.assertEqual(arch.name, 'amd64')

    def test_package_arch_str(self):
        """Test PackageArchitecture __str__ method."""
        arch = PackageArchitecture.objects.create(name='amd64')
        self.assertEqual(str(arch), 'amd64')

    def test_package_arch_unique_name(self):
        """Test PackageArchitecture name is unique."""
        PackageArchitecture.objects.create(name='amd64')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            PackageArchitecture.objects.create(name='amd64')

    def test_common_package_architectures(self):
        """Test common package architecture values."""
        archs = ['amd64', 'i386', 'all', 'noarch', 'x86_64', 'arm64']
        for name in archs:
            arch = PackageArchitecture.objects.create(name=name)
            self.assertEqual(str(arch), name)
