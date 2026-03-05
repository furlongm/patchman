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
class RepositoryMethodTests(TestCase):
    """Tests for Repository model methods."""

    def setUp(self):
        """Set up test data."""
        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.repo = Repository.objects.create(
            name='ubuntu-main',
            arch=self.arch,
            repotype='D',
            enabled=True,
        )

    def test_repository_get_absolute_url(self):
        """Test Repository.get_absolute_url()."""
        url = self.repo.get_absolute_url()
        self.assertIn(str(self.repo.id), url)

    def test_repository_str(self):
        """Test Repository __str__ method."""
        self.assertEqual(str(self.repo), 'ubuntu-main')

    def test_repository_type_constants(self):
        """Test Repository type constants."""
        self.assertEqual(Repository.RPM, 'R')
        self.assertEqual(Repository.DEB, 'D')
        self.assertEqual(Repository.ARCH, 'A')
        self.assertEqual(Repository.GENTOO, 'G')

    def test_repository_enabled_default(self):
        """Test Repository enabled defaults to True."""
        repo = Repository.objects.create(
            name='test-repo', arch=self.arch, repotype='D'
        )
        self.assertTrue(repo.enabled)

    def test_repository_security_default(self):
        """Test Repository security defaults to False."""
        repo = Repository.objects.create(
            name='test-repo', arch=self.arch, repotype='D'
        )
        self.assertFalse(repo.security)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class MirrorMethodTests(TestCase):
    """Tests for Mirror model methods."""

    def setUp(self):
        """Set up test data."""
        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.repo = Repository.objects.create(
            name='ubuntu-main',
            arch=self.arch,
            repotype='D',
        )
        self.mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64',
        )

    def test_mirror_str(self):
        """Test Mirror __str__ method returns URL."""
        self.assertEqual(str(self.mirror), self.mirror.url)

    def test_mirror_get_absolute_url(self):
        """Test Mirror.get_absolute_url()."""
        url = self.mirror.get_absolute_url()
        self.assertIn(str(self.mirror.id), url)

    def test_mirror_enabled_default(self):
        """Test Mirror enabled defaults to True."""
        mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://example.com/repo',
        )
        self.assertTrue(mirror.enabled)

    def test_mirror_refresh_default(self):
        """Test Mirror refresh defaults to True."""
        mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://example.com/repo2',
        )
        self.assertTrue(mirror.refresh)

    def test_mirror_fail_count_default(self):
        """Test Mirror fail_count defaults to 0."""
        mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://example.com/repo3',
        )
        self.assertEqual(mirror.fail_count, 0)

    def test_mirror_last_access_ok_default(self):
        """Test Mirror last_access_ok defaults to False."""
        mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://example.com/repo4',
        )
        self.assertFalse(mirror.last_access_ok)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class MirrorPackageMethodTests(TestCase):
    """Tests for MirrorPackage model."""

    def setUp(self):
        """Set up test data."""
        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.pkg_arch = PackageArchitecture.objects.create(name='amd64')
        self.repo = Repository.objects.create(
            name='ubuntu-main',
            arch=self.arch,
            repotype='D',
        )
        self.mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64',
        )
        self.pkg_name = PackageName.objects.create(name='nginx')
        self.package = Package.objects.create(
            name=self.pkg_name, arch=self.pkg_arch,
            epoch='', version='1.18.0', release='1', packagetype='D'
        )

    def test_mirror_package_creation(self):
        """Test creating a MirrorPackage relationship."""
        mp = MirrorPackage.objects.create(
            mirror=self.mirror,
            package=self.package,
            enabled=True,
        )
        self.assertEqual(mp.mirror, self.mirror)
        self.assertEqual(mp.package, self.package)
        self.assertTrue(mp.enabled)

    def test_mirror_package_enabled_default(self):
        """Test MirrorPackage enabled defaults to True."""
        mp = MirrorPackage.objects.create(
            mirror=self.mirror,
            package=self.package,
        )
        self.assertTrue(mp.enabled)

    def test_mirror_packages_relationship(self):
        """Test Mirror.packages ManyToMany via MirrorPackage."""
        MirrorPackage.objects.create(
            mirror=self.mirror,
            package=self.package,
        )
        self.assertIn(self.package, self.mirror.packages.all())

    def test_package_repo_count(self):
        """Test Package.repo_count() method."""
        MirrorPackage.objects.create(
            mirror=self.mirror,
            package=self.package,
        )
        self.assertEqual(self.package.repo_count(), 1)
