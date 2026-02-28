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

from django.db.models import Q
from django.test import TestCase, override_settings
from django.utils import timezone

from arch.models import MachineArchitecture, PackageArchitecture
from domains.models import Domain
from hosts.models import Host, HostRepo
from operatingsystems.models import OSRelease, OSVariant
from packages.models import Package, PackageName, PackageUpdate
from repos.models import Mirror, MirrorPackage, Repository


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


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class KernelUpdateTests(TestCase):
    """Tests for kernel update detection logic."""

    def setUp(self):
        """Set up test data with RPM kernel packages."""
        self.m_arch = MachineArchitecture.objects.create(name='x86_64')
        self.domain = Domain.objects.create(name='example.com')
        self.os_release = OSRelease.objects.create(
            name='Rocky Linux 9', codename=''
        )
        self.os_variant = OSVariant.objects.create(
            name='Rocky Linux 9.4', osrelease=self.os_release
        )
        self.pkg_arch = PackageArchitecture.objects.create(name='x86_64')
        self.kernel_name = PackageName.objects.create(name='kernel-core')

        # create kernel packages at three versions
        self.kernel_362 = Package.objects.create(
            name=self.kernel_name, arch=self.pkg_arch, epoch='0',
            version='5.14.0', release='362.el9', packagetype='R'
        )
        self.kernel_427 = Package.objects.create(
            name=self.kernel_name, arch=self.pkg_arch, epoch='0',
            version='5.14.0', release='427.el9', packagetype='R'
        )
        self.kernel_503 = Package.objects.create(
            name=self.kernel_name, arch=self.pkg_arch, epoch='0',
            version='5.14.0', release='503.el9', packagetype='R'
        )

        # set up a repo with the latest kernel
        self.repo = Repository.objects.create(
            name='baseos', repotype='R', arch=self.m_arch,
        )
        self.mirror = Mirror.objects.create(
            repo=self.repo, url='http://repo.example.com/baseos',
        )
        self.mirror.packages.add(self.kernel_503)

    def _create_host(self, running_kernel, installed_kernels):
        """Helper to create a host with a running kernel and installed packages."""
        host = Host.objects.create(
            hostname='rocky.example.com',
            ipaddress='192.168.1.50',
            osvariant=self.os_variant,
            kernel=running_kernel,
            arch=self.m_arch,
            domain=self.domain,
            lastreport=timezone.now(),
            host_repos_only=False,
        )
        host.packages.set(installed_kernels)
        return host

    def test_latest_installed_not_running(self):
        """Scenario 1: latest kernel installed but not running.

        Old kernels should not show as updates.
        Running→latest should be an update + reboot required.
        """
        host = self._create_host(
            '5.14.0-362.el9',
            [self.kernel_362, self.kernel_427, self.kernel_503],
        )
        repo_packages = Package.objects.filter(mirror=self.mirror)
        kernel_packages = host.packages.filter(name=self.kernel_name)

        host.find_kernel_updates(kernel_packages, repo_packages)

        self.assertEqual(host.updates.count(), 1)
        update = host.updates.first()
        self.assertEqual(update.oldpackage, self.kernel_362)
        self.assertEqual(update.newpackage, self.kernel_503)
        self.assertTrue(host.reboot_required)

    def test_latest_installed_and_running(self):
        """Scenario 2: latest kernel installed and running.

        No updates should be generated.
        """
        host = self._create_host(
            '5.14.0-503.el9',
            [self.kernel_362, self.kernel_427, self.kernel_503],
        )
        repo_packages = Package.objects.filter(mirror=self.mirror)
        kernel_packages = host.packages.filter(name=self.kernel_name)

        host.find_kernel_updates(kernel_packages, repo_packages)

        self.assertEqual(host.updates.count(), 0)
        self.assertFalse(host.reboot_required)

    def test_latest_not_installed(self):
        """Scenario 3: latest kernel not installed.

        Update from running to repo highest.
        """
        host = self._create_host(
            '5.14.0-427.el9',
            [self.kernel_362, self.kernel_427],
        )
        repo_packages = Package.objects.filter(mirror=self.mirror)
        kernel_packages = host.packages.filter(name=self.kernel_name)

        host.find_kernel_updates(kernel_packages, repo_packages)

        self.assertEqual(host.updates.count(), 1)
        update = host.updates.first()
        self.assertEqual(update.oldpackage, self.kernel_427)
        self.assertEqual(update.newpackage, self.kernel_503)

    def test_running_newer_than_repo(self):
        """Scenario 5: running kernel is newer than repo highest.

        No updates should be generated.
        """
        kernel_600 = Package.objects.create(
            name=self.kernel_name, arch=self.pkg_arch, epoch='0',
            version='5.14.0', release='600.el9', packagetype='R'
        )
        host = self._create_host(
            '5.14.0-600.el9',
            [self.kernel_503, kernel_600],
        )
        repo_packages = Package.objects.filter(mirror=self.mirror)
        kernel_packages = host.packages.filter(name=self.kernel_name)

        host.find_kernel_updates(kernel_packages, repo_packages)

        self.assertEqual(host.updates.count(), 0)

    def test_old_kernels_not_generating_duplicate_updates(self):
        """Old kernels should not each generate their own update."""
        host = self._create_host(
            '5.14.0-427.el9',
            [self.kernel_362, self.kernel_427],
        )
        repo_packages = Package.objects.filter(mirror=self.mirror)
        kernel_packages = host.packages.filter(name=self.kernel_name)

        host.find_kernel_updates(kernel_packages, repo_packages)

        # should be exactly 1 update, not 2
        self.assertEqual(host.updates.count(), 1)

    def test_rpm_uname_with_arch_suffix(self):
        """RPM: uname -r with .x86_64 suffix should still match correctly."""
        host = self._create_host(
            '5.14.0-503.el9.x86_64',
            [self.kernel_362, self.kernel_427, self.kernel_503],
        )
        repo_packages = Package.objects.filter(mirror=self.mirror)
        kernel_packages = host.packages.filter(name=self.kernel_name)

        host.find_kernel_updates(kernel_packages, repo_packages)

        self.assertEqual(host.updates.count(), 0)
        host.refresh_from_db()
        self.assertFalse(host.reboot_required)

    def test_suse_uname_truncated_release(self):
        """SUSE: uname -r truncates micro release and appends flavour."""
        suse_name = PackageName.objects.create(name='kernel-default')
        pkg_8 = Package.objects.create(
            name=suse_name, arch=self.pkg_arch, epoch='0',
            version='6.12.0', release='160000.8.1', packagetype='R'
        )
        pkg_25 = Package.objects.create(
            name=suse_name, arch=self.pkg_arch, epoch='0',
            version='6.12.0', release='160000.25.1', packagetype='R'
        )
        suse_repo = Repository.objects.create(
            name='oss', repotype='R', arch=self.m_arch,
            security=False, enabled=True,
        )
        suse_mirror = Mirror.objects.create(
            repo=suse_repo, url='http://download.opensuse.org/oss',
        )
        MirrorPackage.objects.create(mirror=suse_mirror, package=pkg_8)
        MirrorPackage.objects.create(mirror=suse_mirror, package=pkg_25)

        # running 160000.8, installed 160000.8 and 160000.25
        # uname shows '6.12.0-160000.8-default' (truncated, with flavour)
        host = self._create_host(
            '6.12.0-160000.8-default',
            [pkg_8, pkg_25],
        )
        host.repos.add(suse_repo)
        repo_packages = Package.objects.filter(mirror=suse_mirror)
        kernel_packages = host.packages.filter(name=suse_name)

        host.find_kernel_updates(kernel_packages, repo_packages)

        # running 8 < installed 25 → one update, reboot required
        self.assertEqual(host.updates.count(), 1)
        host.refresh_from_db()
        self.assertTrue(host.reboot_required)

    def test_suse_uname_running_is_highest(self):
        """SUSE: running kernel matches highest installed (no reboot)."""
        suse_name = PackageName.objects.create(name='kernel-default')
        pkg_25 = Package.objects.create(
            name=suse_name, arch=self.pkg_arch, epoch='0',
            version='6.12.0', release='160000.25.1', packagetype='R'
        )
        suse_repo = Repository.objects.create(
            name='oss', repotype='R', arch=self.m_arch,
            security=False, enabled=True,
        )
        suse_mirror = Mirror.objects.create(
            repo=suse_repo, url='http://download.opensuse.org/oss',
        )
        MirrorPackage.objects.create(mirror=suse_mirror, package=pkg_25)

        # running 160000.25 = installed highest 160000.25.1 (truncated match)
        host = self._create_host(
            '6.12.0-160000.25-default',
            [pkg_25],
        )
        host.repos.add(suse_repo)
        repo_packages = Package.objects.filter(mirror=suse_mirror)
        kernel_packages = host.packages.filter(name=suse_name)

        host.find_kernel_updates(kernel_packages, repo_packages)

        self.assertEqual(host.updates.count(), 0)
        host.refresh_from_db()
        self.assertFalse(host.reboot_required)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class DebKernelUpdateTests(TestCase):
    """Tests for DEB kernel update detection logic."""

    def setUp(self):
        """Set up test data with DEB kernel packages."""
        self.m_arch = MachineArchitecture.objects.create(name='x86_64')
        self.domain = Domain.objects.create(name='example.com')
        self.os_release = OSRelease.objects.create(
            name='Ubuntu 24.04', codename='noble'
        )
        self.os_variant = OSVariant.objects.create(
            name='Ubuntu 24.04.1 LTS', osrelease=self.os_release
        )
        self.pkg_arch = PackageArchitecture.objects.create(name='amd64')

        # DEB kernel package names — each version is a different package name
        self.img_49_name = PackageName.objects.create(name='linux-image-6.8.0-49-generic')
        self.img_51_name = PackageName.objects.create(name='linux-image-6.8.0-51-generic')
        self.img_53_name = PackageName.objects.create(name='linux-image-6.8.0-53-generic')

        self.img_49 = Package.objects.create(
            name=self.img_49_name, arch=self.pkg_arch, epoch='',
            version='6.8.0-49.50', release='', packagetype='D'
        )
        self.img_51 = Package.objects.create(
            name=self.img_51_name, arch=self.pkg_arch, epoch='',
            version='6.8.0-51.52', release='', packagetype='D'
        )
        self.img_53 = Package.objects.create(
            name=self.img_53_name, arch=self.pkg_arch, epoch='',
            version='6.8.0-53.54', release='', packagetype='D'
        )

        # repo has the latest kernel
        self.repo = Repository.objects.create(
            name='noble-security', repotype='D', arch=self.m_arch,
        )
        from repos.models import Mirror
        self.mirror = Mirror.objects.create(
            repo=self.repo, url='http://archive.ubuntu.com/ubuntu',
        )
        self.mirror.packages.add(self.img_49, self.img_51, self.img_53)

    def _create_host(self, running_kernel, installed_kernels):
        host = Host.objects.create(
            hostname='ubuntu.example.com',
            ipaddress='192.168.1.60',
            osvariant=self.os_variant,
            kernel=running_kernel,
            arch=self.m_arch,
            domain=self.domain,
            lastreport=timezone.now(),
            host_repos_only=False,
        )
        host.packages.set(installed_kernels)
        return host

    def test_deb_latest_installed_not_running(self):
        """DEB: latest kernel installed but not running.

        Should show update from running→latest. Old kernels ignored.
        """
        host = self._create_host(
            '6.8.0-49-generic',
            [self.img_49, self.img_51, self.img_53],
        )
        repo_packages = Package.objects.filter(mirror=self.mirror)
        kernel_packages = host.packages.filter(
            name__name__startswith='linux-image-'
        )

        host.find_kernel_updates(kernel_packages, repo_packages)

        self.assertEqual(host.updates.count(), 1)
        update = host.updates.first()
        self.assertEqual(update.oldpackage, self.img_49)
        self.assertEqual(update.newpackage, self.img_53)

    def test_deb_latest_installed_and_running(self):
        """DEB: latest kernel installed and running. No updates."""
        host = self._create_host(
            '6.8.0-53-generic',
            [self.img_49, self.img_51, self.img_53],
        )
        repo_packages = Package.objects.filter(mirror=self.mirror)
        kernel_packages = host.packages.filter(
            name__name__startswith='linux-image-'
        )

        host.find_kernel_updates(kernel_packages, repo_packages)

        self.assertEqual(host.updates.count(), 0)

    def test_deb_latest_not_installed(self):
        """DEB: repo has newer kernel not yet installed."""
        host = self._create_host(
            '6.8.0-51-generic',
            [self.img_49, self.img_51],
        )
        repo_packages = Package.objects.filter(mirror=self.mirror)
        kernel_packages = host.packages.filter(
            name__name__startswith='linux-image-'
        )

        host.find_kernel_updates(kernel_packages, repo_packages)

        self.assertEqual(host.updates.count(), 1)
        update = host.updates.first()
        self.assertEqual(update.oldpackage, self.img_51)
        self.assertEqual(update.newpackage, self.img_53)

    def test_deb_flavour_extraction(self):
        """Test _get_deb_kernel_flavour helper."""
        host = self._create_host('6.8.0-51-generic', [self.img_51])
        self.assertEqual(
            host._get_deb_kernel_flavour('linux-image-6.8.0-51-generic'),
            'generic'
        )
        self.assertEqual(
            host._get_deb_kernel_flavour('linux-modules-extra-6.8.0-51-lowlatency'),
            'lowlatency'
        )
        self.assertEqual(
            host._get_deb_kernel_flavour('linux-image-6.1.0-28-cloud-amd64'),
            'cloud-amd64'
        )
        self.assertEqual(
            host._get_deb_kernel_flavour('linux-image-unsigned-6.8.0-51-generic'),
            'generic'
        )

    def test_deb_running_kernel_flavour(self):
        """Test _get_running_kernel_flavour helper."""
        host = self._create_host('6.8.0-51-generic', [self.img_51])
        self.assertEqual(host._get_running_kernel_flavour(), 'generic')

        host.kernel = '6.1.0-28-cloud-amd64'
        self.assertEqual(host._get_running_kernel_flavour(), 'cloud-amd64')

        host.kernel = '5.14.0-503.el9'
        self.assertIsNone(host._get_running_kernel_flavour())


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ArchKernelUpdateTests(TestCase):
    """Tests for Arch Linux kernel update detection and reboot check."""

    def setUp(self):
        self.m_arch = MachineArchitecture.objects.create(name='x86_64')
        self.domain = Domain.objects.create(name='example.com')
        self.os_release = OSRelease.objects.create(
            name='Arch Linux', codename='arch'
        )
        self.os_variant = OSVariant.objects.create(
            name='Arch Linux', osrelease=self.os_release
        )
        self.pkg_arch = PackageArchitecture.objects.create(name='x86_64')

        self.linux_name = PackageName.objects.create(name='linux')
        self.linux_headers_name = PackageName.objects.create(name='linux-headers')

        self.linux_installed = Package.objects.create(
            name=self.linux_name, arch=self.pkg_arch, epoch='',
            version='6.12.8.arch1', release='1', packagetype='A'
        )
        self.linux_headers_installed = Package.objects.create(
            name=self.linux_headers_name, arch=self.pkg_arch, epoch='',
            version='6.12.8.arch1', release='1', packagetype='A'
        )
        self.linux_repo = Package.objects.create(
            name=self.linux_name, arch=self.pkg_arch, epoch='',
            version='6.12.10.arch1', release='1', packagetype='A'
        )
        self.linux_headers_repo = Package.objects.create(
            name=self.linux_headers_name, arch=self.pkg_arch, epoch='',
            version='6.12.10.arch1', release='1', packagetype='A'
        )

        self.repo = Repository.objects.create(
            name='core', repotype='A', arch=self.m_arch,
        )
        from repos.models import Mirror
        self.mirror = Mirror.objects.create(
            repo=self.repo, url='https://mirror.archlinux.org/core',
        )
        self.mirror.packages.add(self.linux_repo, self.linux_headers_repo)

    def _create_host(self, running_kernel, installed_pkgs):
        host = Host.objects.create(
            hostname='arch.example.com',
            ipaddress='192.168.1.70',
            osvariant=self.os_variant,
            kernel=running_kernel,
            arch=self.m_arch,
            domain=self.domain,
            lastreport=timezone.now(),
            host_repos_only=False,
        )
        host.packages.set(installed_pkgs)
        return host

    def test_arch_update_available(self):
        """Arch: installed kernel older than repo → update."""
        host = self._create_host(
            '6.12.8-arch1-1',
            [self.linux_installed, self.linux_headers_installed],
        )
        repo_packages = Package.objects.filter(mirror=self.mirror)
        kernel_packages = host.packages.filter(
            Q(name=self.linux_name) | Q(name=self.linux_headers_name)
        )

        host.find_kernel_updates(kernel_packages, repo_packages)

        self.assertEqual(host.updates.count(), 2)

    def test_arch_no_update(self):
        """Arch: installed matches repo → no update."""
        host = self._create_host(
            '6.12.10-arch1-1',
            [self.linux_repo, self.linux_headers_repo],
        )
        repo_packages = Package.objects.filter(mirror=self.mirror)
        kernel_packages = host.packages.filter(
            Q(name=self.linux_name) | Q(name=self.linux_headers_name)
        )

        host.find_kernel_updates(kernel_packages, repo_packages)

        self.assertEqual(host.updates.count(), 0)

    def test_arch_reboot_required(self):
        """Arch: installed kernel newer than running → reboot required."""
        host = self._create_host(
            '6.12.8-arch1-1',
            [self.linux_repo, self.linux_headers_repo],
        )
        repo_packages = Package.objects.filter(mirror=self.mirror)
        kernel_packages = host.packages.filter(
            Q(name=self.linux_name) | Q(name=self.linux_headers_name)
        )

        host.find_kernel_updates(kernel_packages, repo_packages)

        host.refresh_from_db()
        self.assertTrue(host.reboot_required)

    def test_arch_no_reboot_when_current(self):
        """Arch: running matches installed → no reboot."""
        host = self._create_host(
            '6.12.10-arch1-1',
            [self.linux_repo, self.linux_headers_repo],
        )
        repo_packages = Package.objects.filter(mirror=self.mirror)
        kernel_packages = host.packages.filter(
            Q(name=self.linux_name) | Q(name=self.linux_headers_name)
        )

        host.find_kernel_updates(kernel_packages, repo_packages)

        host.refresh_from_db()
        self.assertFalse(host.reboot_required)
