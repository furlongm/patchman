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
from packages.models import Package, PackageName
from repos.models import Mirror, MirrorPackage, Repository


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class MirrorPackageTests(TestCase):
    """Tests for MirrorPackage operations."""

    def setUp(self):
        """Set up test data."""
        self.machine_arch = MachineArchitecture.objects.create(name='x86_64')
        self.pkg_arch = PackageArchitecture.objects.create(name='x86_64')
        self.repo = Repository.objects.create(
            name='test-repo',
            arch=self.machine_arch,
            repotype=Repository.RPM,
        )
        self.mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://mirror.example.com/repo',
        )

    def test_add_package_to_mirror(self):
        """Test adding a package to mirror."""
        pkg_name = PackageName.objects.create(name='httpd')
        pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='2.4.57',
            release='1.el9',
            packagetype=Package.RPM,
        )

        MirrorPackage.objects.create(mirror=self.mirror, package=pkg)
        self.assertEqual(self.mirror.packages.count(), 1)
        self.assertIn(pkg, self.mirror.packages.all())

    def test_remove_package_from_mirror(self):
        """Test removing a package from mirror."""
        pkg_name = PackageName.objects.create(name='nginx')
        pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='1.20.0',
            release='1.el9',
            packagetype=Package.RPM,
        )

        mp = MirrorPackage.objects.create(mirror=self.mirror, package=pkg)
        self.assertEqual(self.mirror.packages.count(), 1)

        mp.delete()
        self.assertEqual(self.mirror.packages.count(), 0)

    def test_mirror_package_unique_constraint(self):
        """Test that same package can't be added twice to mirror."""
        pkg_name = PackageName.objects.create(name='curl')
        pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='7.76.0',
            release='1.el9',
            packagetype=Package.RPM,
        )

        MirrorPackage.objects.create(mirror=self.mirror, package=pkg)

        # get_or_create should return existing, not create new
        mp, created = MirrorPackage.objects.get_or_create(mirror=self.mirror, package=pkg)
        self.assertFalse(created)
        self.assertEqual(self.mirror.packages.count(), 1)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class MirrorModelTests(TestCase):
    """Tests for Mirror model methods."""

    def setUp(self):
        """Set up test data."""
        self.machine_arch = MachineArchitecture.objects.create(name='x86_64')
        self.repo = Repository.objects.create(
            name='test-repo',
            arch=self.machine_arch,
            repotype=Repository.RPM,
        )
        self.mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://mirror.example.com/repo',
            enabled=True,
            refresh=True,
        )

    def test_mirror_fail_increments_count(self):
        """Test that fail() increments fail_count."""
        initial_count = self.mirror.fail_count
        self.mirror.fail()
        self.mirror.refresh_from_db()
        self.assertEqual(self.mirror.fail_count, initial_count + 1)

    def test_mirror_fail_disables_after_threshold(self):
        """Test that mirror is disabled after too many failures."""
        # Set fail count near threshold
        self.mirror.fail_count = 27  # Default threshold is 28
        self.mirror.save()

        self.mirror.fail()
        self.mirror.refresh_from_db()

        self.assertFalse(self.mirror.refresh)

    def test_mirror_str(self):
        """Test mirror string representation."""
        self.assertIn(self.mirror.url, str(self.mirror))
