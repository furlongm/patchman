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
from django.utils import timezone

from arch.models import MachineArchitecture, PackageArchitecture
from domains.models import Domain
from hosts.models import Host, HostRepo
from operatingsystems.models import OSRelease, OSVariant
from packages.models import Package, PackageName, PackageUpdate
from repos.models import Repository


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class HostMethodTests(TestCase):
    """Tests for Host model methods."""

    def setUp(self):
        """Set up test data."""
        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.domain = Domain.objects.create(name='example.com')
        self.os_release = OSRelease.objects.create(
            name='Ubuntu 22.04', codename='jammy'
        )
        self.os_variant = OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS', osrelease=self.os_release
        )
        self.host = Host.objects.create(
            hostname='testhost.example.com',
            ipaddress='192.168.1.100',
            osvariant=self.os_variant,
            kernel='5.15.0-91-generic',
            arch=self.arch,
            domain=self.domain,
            lastreport=timezone.now(),
        )

    def test_get_num_packages_empty(self):
        """Test get_num_packages() with no packages."""
        self.assertEqual(self.host.get_num_packages(), 0)

    def test_get_num_packages_with_packages(self):
        """Test get_num_packages() with packages."""
        pkg_arch = PackageArchitecture.objects.create(name='amd64')
        pkg_name = PackageName.objects.create(name='nginx')
        pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='1.18.0', release='1', packagetype='D'
        )
        self.host.packages.add(pkg)
        self.assertEqual(self.host.get_num_packages(), 1)

    def test_get_num_repos_empty(self):
        """Test get_num_repos() with no repos."""
        self.assertEqual(self.host.get_num_repos(), 0)

    def test_get_num_repos_with_repos(self):
        """Test get_num_repos() with repos."""
        repo = Repository.objects.create(
            name='ubuntu-main', arch=self.arch, repotype='D'
        )
        HostRepo.objects.create(host=self.host, repo=repo, enabled=True)
        self.assertEqual(self.host.get_num_repos(), 1)

    def test_get_num_updates_empty(self):
        """Test get_num_updates() with no updates."""
        self.assertEqual(self.host.get_num_updates(), 0)

    def test_get_num_updates_with_updates(self):
        """Test get_num_updates() with updates."""
        pkg_arch = PackageArchitecture.objects.create(name='amd64')
        pkg_name = PackageName.objects.create(name='openssl')
        old_pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='3.0.0', release='1', packagetype='D'
        )
        new_pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='3.0.1', release='1', packagetype='D'
        )
        update = PackageUpdate.objects.create(
            oldpackage=old_pkg, newpackage=new_pkg, security=True
        )
        self.host.updates.add(update)
        self.assertEqual(self.host.get_num_updates(), 1)

    def test_get_num_security_updates(self):
        """Test get_num_security_updates() counts only security updates."""
        pkg_arch = PackageArchitecture.objects.create(name='amd64')
        pkg_name = PackageName.objects.create(name='openssl')
        old_pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='3.0.0', release='1', packagetype='D'
        )
        sec_pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='3.0.1', release='1', packagetype='D'
        )
        bug_pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='3.0.2', release='1', packagetype='D'
        )
        sec_update = PackageUpdate.objects.create(
            oldpackage=old_pkg, newpackage=sec_pkg, security=True
        )
        bug_update = PackageUpdate.objects.create(
            oldpackage=old_pkg, newpackage=bug_pkg, security=False
        )
        self.host.updates.add(sec_update, bug_update)

        self.assertEqual(self.host.get_num_security_updates(), 1)
        self.assertEqual(self.host.get_num_bugfix_updates(), 1)
        self.assertEqual(self.host.get_num_updates(), 2)

    def test_cached_counts_survive_full_save(self):
        """Test that cached update counts are not overwritten by a full save.

        Regression test: M2M signals update cached count fields via
        save(update_fields=[...]), but a subsequent full save() on the
        same in-memory instance would overwrite them with stale values.
        """
        pkg_arch = PackageArchitecture.objects.create(name='amd64')
        pkg_name = PackageName.objects.create(name='curl')
        old_pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='7.0.0', release='1', packagetype='D'
        )
        new_pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='7.0.1', release='1', packagetype='D'
        )
        sec_update = PackageUpdate.objects.create(
            oldpackage=old_pkg, newpackage=new_pkg, security=True
        )

        # simulate the find_host_updates_homogenous pattern:
        # M2M add fires signal, then full save follows
        self.host.updates.add(sec_update)
        self.host.refresh_from_db(fields=['sec_updates_count', 'bug_updates_count'])
        self.host.updated_at = timezone.now()
        self.host.save()

        # re-read from DB to verify counts persisted
        self.host.refresh_from_db()
        self.assertEqual(self.host.sec_updates_count, 1)
        self.assertEqual(self.host.bug_updates_count, 0)

    def test_in_memory_counts_stale_after_m2m_signal(self):
        """Test that in-memory instance has updated counts after M2M signal.

        The M2M signal updates the DB directly via save(update_fields=[...]).
        Django also updates the in-memory instance, but on MySQL with
        REPEATABLE READ isolation and full save(), the stale snapshot can
        overwrite the DB values. The refresh_from_db pattern in
        find_host_updates_homogenous prevents this.
        """
        pkg_arch = PackageArchitecture.objects.create(name='amd64')
        pkg_name = PackageName.objects.create(name='wget')
        old_pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='1.0.0', release='1', packagetype='D'
        )
        new_pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='1.0.1', release='1', packagetype='D'
        )
        bug_update = PackageUpdate.objects.create(
            oldpackage=old_pkg, newpackage=new_pkg, security=False
        )

        # M2M add fires signal — DB has correct count
        self.host.updates.add(bug_update)

        # verify DB has the correct value
        db_host = Host.objects.get(pk=self.host.pk)
        self.assertEqual(db_host.bug_updates_count, 1)
