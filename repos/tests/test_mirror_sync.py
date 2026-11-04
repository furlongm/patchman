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

from unittest.mock import patch

from django.test import TestCase, override_settings

from arch.models import MachineArchitecture, PackageArchitecture
from packages.models import Package, PackageName
from repos.models import Mirror, MirrorPackage, Repository
from repos.utils import (
    add_mirrors_from_urls, check_for_mirrorlists, get_latest_mirrorlist_url,
)

AL2023 = 'https://cdn.amazonlinux.com/al2023/core'


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


@override_settings(MAX_MIRRORS=2)
class MirrorlistTests(TestCase):
    """Tests for adding mirrors from mirrorlists."""

    def setUp(self):
        arch = MachineArchitecture.objects.create(name='x86_64')
        self.repo = Repository.objects.create(
            name='Amazon Linux 2023 repository',
            arch=arch,
            repotype=Repository.RPM,
        )

    def _urls(self):
        return set(self.repo.mirror_set.values_list('url', flat=True))

    def test_mirrors_limited_to_max(self):
        """Test only MAX_MIRRORS mirrors are added from a list."""
        add_mirrors_from_urls(self.repo, [f'http://m{i}.example.com/repo' for i in range(5)])
        self.assertEqual(self.repo.mirror_set.count(), 2)

    def test_previous_mirrors_do_not_block_current(self):
        """Test mirrors no longer in the list do not count towards the limit."""
        for guid in ('a' * 64, 'b' * 64):
            Mirror.objects.create(repo=self.repo, url=f'{AL2023}/guids/{guid}/x86_64')
        current = f'{AL2023}/guids/{"c" * 64}/x86_64'
        add_mirrors_from_urls(self.repo, [current + '/'])
        self.assertIn(current, self._urls())

    def test_metalink_and_mirrorlist_urls_match(self):
        """Test metalink repomd.xml urls are stored like mirrorlist base urls."""
        base = 'http://m.example.com/repo/os'
        add_mirrors_from_urls(self.repo, [f'{base}/repodata/repomd.xml'])
        add_mirrors_from_urls(self.repo, [f'{base}/'])
        self.assertEqual(self._urls(), {base})

    def test_latest_mirrorlist_url(self):
        """Test pinned AL2023 mirrorlists map to the moving latest one."""
        pinned = f'{AL2023}/mirrors/2023.12.20261102/x86_64/mirror.list'
        self.assertEqual(
            get_latest_mirrorlist_url(pinned),
            f'{AL2023}/mirrors/latest/x86_64/mirror.list',
        )
        regional = 'https://al2023-repos-us-east-1-de612dc2.s3.dualstack.us-east-1.amazonaws.com/core/mirrors'
        self.assertEqual(
            get_latest_mirrorlist_url(f'{regional}/2023.6.20241010/SRPMS/mirror.list'),
            f'{regional}/latest/SRPMS/mirror.list',
        )
        local = 'http://mirror.example.com/al2027/core/mirrors'
        self.assertEqual(
            get_latest_mirrorlist_url(f'{local}/2027.0.20260803/aarch64/mirror.list'),
            f'{local}/latest/aarch64/mirror.list',
        )
        al2 = 'https://amazonlinux-2-repos-us-east-1.s3.dualstack.us-east-1.amazonaws.com/2/core'
        self.assertEqual(
            get_latest_mirrorlist_url(f'{al2}/2.0.20231101.0/x86_64/mirror.list'),
            f'{al2}/latest/x86_64/mirror.list',
        )
        self.assertIsNone(get_latest_mirrorlist_url(f'{AL2023}/mirrors/latest/x86_64/mirror.list'))
        self.assertIsNone(get_latest_mirrorlist_url(f'{al2}/latest/x86_64/mirror.list'))
        self.assertIsNone(get_latest_mirrorlist_url('https://mirrors.example.com/mirrorlist?repo=x'))

    def test_pinned_mirrorlist_follows_latest(self):
        """Test a repo with only a pinned mirrorlist also gets the latest release."""
        pinned = f'{AL2023}/mirrors/2023.6.20241010/x86_64/mirror.list'
        latest = f'{AL2023}/mirrors/latest/x86_64/mirror.list'
        old_guid = f'{AL2023}/guids/{"a" * 64}/x86_64'
        new_guid = f'{AL2023}/guids/{"b" * 64}/x86_64'
        Mirror.objects.create(repo=self.repo, url=pinned)
        lists = {pinned: [old_guid + '/'], latest: [new_guid + '/']}
        with patch('repos.utils.get_mirrorlist_urls', side_effect=lambda url: lists.get(url)):
            check_for_mirrorlists(self.repo)
        self.assertEqual(self._urls(), {pinned, latest, old_guid, new_guid})
        self.assertTrue(Mirror.objects.get(url=latest).mirrorlist)

    def test_missing_latest_mirrorlist_not_added(self):
        """Test the latest mirrorlist is not added if it does not exist, e.g. on a local mirror."""
        pinned = 'http://mirror.example.com/al2023/core/mirrors/2023.6.20241010/x86_64/mirror.list'
        guid = f'http://mirror.example.com/al2023/core/guids/{"a" * 64}/x86_64'
        Mirror.objects.create(repo=self.repo, url=pinned)
        lists = {pinned: [guid]}
        with patch('repos.utils.get_mirrorlist_urls', side_effect=lambda url: lists.get(url)):
            check_for_mirrorlists(self.repo)
        self.assertEqual(self._urls(), {pinned, guid})
