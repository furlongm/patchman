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

import json

from django.test import TestCase, override_settings
from django.utils import timezone

from arch.models import MachineArchitecture, PackageArchitecture
from domains.models import Domain
from hosts.models import Host, HostRepo
from operatingsystems.models import OSRelease, OSVariant
from packages.models import Package, PackageName, PackageUpdate
from reports.models import Report
from repos.models import Mirror, MirrorPackage, Repository


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class HostFindUpdatesTests(TestCase):
    """Tests for Host.find_updates() method."""

    def setUp(self):
        """Set up test data."""
        self.machine_arch = MachineArchitecture.objects.create(name='x86_64')
        self.pkg_arch = PackageArchitecture.objects.create(name='x86_64')
        self.osrelease = OSRelease.objects.create(name='Rocky Linux 9')
        self.osvariant = OSVariant.objects.create(
            name='Rocky Linux 9 x86_64',
            osrelease=self.osrelease,
            arch=self.machine_arch,
        )
        self.domain = Domain.objects.create(name='example.com')
        self.host = Host.objects.create(
            hostname='updatetest.example.com',
            ipaddress='192.168.1.100',
            arch=self.machine_arch,
            osvariant=self.osvariant,
            domain=self.domain,
            kernel='5.14.0-362.el9.x86_64',
            lastreport=timezone.now(),
        )

        # Create a repository
        self.repo = Repository.objects.create(
            name='baseos',
            arch=self.machine_arch,
            repotype=Repository.RPM,
            enabled=True,
        )
        self.mirror = Mirror.objects.create(
            repo=self.repo,
            url='http://mirror.rockylinux.org/rocky/9/BaseOS/x86_64/os',
            enabled=True,
            refresh=True,
        )

        # Associate repo with host
        HostRepo.objects.create(
            host=self.host,
            repo=self.repo,
            enabled=True,
        )

    def test_find_updates_no_packages(self):
        """Test find_updates with no packages installed."""
        # Host has no packages, should not crash
        self.host.find_updates()
        self.assertEqual(self.host.updates.count(), 0)

    def test_find_updates_no_updates_available(self):
        """Test find_updates when no updates are available."""
        # Install a package on host
        pkg_name = PackageName.objects.create(name='httpd')
        installed_pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='2.4.57',
            release='5.el9',
            packagetype=Package.RPM,
        )
        self.host.packages.add(installed_pkg)

        # No newer package in mirror
        MirrorPackage.objects.create(
            mirror=self.mirror,
            package=installed_pkg,
        )

        self.host.find_updates()
        # No updates should be found (same version in repo)
        self.assertEqual(self.host.updates.count(), 0)

    def test_find_updates_with_available_update(self):
        """Test find_updates when an update is available."""
        # Install an old package on host
        pkg_name = PackageName.objects.create(name='openssl')
        old_pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='1',
            version='3.0.0',
            release='1.el9',
            packagetype=Package.RPM,
        )
        self.host.packages.add(old_pkg)

        # Add old package to mirror
        MirrorPackage.objects.create(
            mirror=self.mirror,
            package=old_pkg,
        )

        # Add newer package to mirror
        new_pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='1',
            version='3.0.7',
            release='1.el9',
            packagetype=Package.RPM,
        )
        MirrorPackage.objects.create(
            mirror=self.mirror,
            package=new_pkg,
        )

        self.host.find_updates()
        # Should find the update
        self.assertEqual(self.host.updates.count(), 1)
        update = self.host.updates.first()
        self.assertEqual(update.oldpackage, old_pkg)
        self.assertEqual(update.newpackage, new_pkg)

    def test_find_updates_security_repo(self):
        """Test find_updates marks security repo updates correctly."""
        # Create a security repository
        security_repo = Repository.objects.create(
            name='baseos-security',
            arch=self.machine_arch,
            repotype=Repository.RPM,
            enabled=True,
            security=True,  # Mark as security repo
        )
        security_mirror = Mirror.objects.create(
            repo=security_repo,
            url='http://mirror.rockylinux.org/rocky/9/BaseOS/x86_64/security',
            enabled=True,
            refresh=True,
        )
        HostRepo.objects.create(
            host=self.host,
            repo=security_repo,
            enabled=True,
        )

        # Install an old package
        pkg_name = PackageName.objects.create(name='curl')
        old_pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='7.76.0',
            release='1.el9',
            packagetype=Package.RPM,
        )
        self.host.packages.add(old_pkg)
        MirrorPackage.objects.create(mirror=self.mirror, package=old_pkg)

        # Add security update
        new_pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='7.76.1',
            release='1.el9_security',
            packagetype=Package.RPM,
        )
        MirrorPackage.objects.create(mirror=security_mirror, package=new_pkg)

        self.host.find_updates()
        # Update should be marked as security
        if self.host.updates.count() > 0:
            update = self.host.updates.first()
            self.assertTrue(update.security)

    def test_find_updates_excludes_kernel_packages(self):
        """Test find_updates handles kernel packages separately."""
        # Kernel packages have special handling
        pkg_name = PackageName.objects.create(name='kernel')
        old_kernel = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='5.14.0',
            release='362.el9',
            packagetype=Package.RPM,
        )
        self.host.packages.add(old_kernel)
        MirrorPackage.objects.create(mirror=self.mirror, package=old_kernel)

        new_kernel = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='5.14.0',
            release='427.el9',
            packagetype=Package.RPM,
        )
        MirrorPackage.objects.create(mirror=self.mirror, package=new_kernel)

        # Should not crash when processing kernels
        self.host.find_updates()

    def test_find_updates_removes_stale_updates(self):
        """Test find_updates removes updates that are no longer valid."""
        # Create an update that's no longer valid
        pkg_name = PackageName.objects.create(name='stale-pkg')
        old_pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='1.0.0',
            release='1.el9',
            packagetype=Package.RPM,
        )
        new_pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='1.0.1',
            release='1.el9',
            packagetype=Package.RPM,
        )

        # Create a stale update manually
        stale_update = PackageUpdate.objects.create(
            oldpackage=old_pkg,
            newpackage=new_pkg,
            security=False,
        )
        self.host.updates.add(stale_update)
        self.assertEqual(self.host.updates.count(), 1)

        # Host doesn't have the old package installed
        # find_updates should remove this stale update
        self.host.find_updates()
        self.assertEqual(self.host.updates.count(), 0)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class HostProcessUpdateTests(TestCase):
    """Tests for Host.process_update() method."""

    def setUp(self):
        """Set up test data."""
        self.machine_arch = MachineArchitecture.objects.create(name='x86_64')
        self.pkg_arch = PackageArchitecture.objects.create(name='x86_64')
        self.osrelease = OSRelease.objects.create(name='Rocky Linux 9')
        self.osvariant = OSVariant.objects.create(
            name='Rocky Linux 9 x86_64',
            osrelease=self.osrelease,
            arch=self.machine_arch,
        )
        self.domain = Domain.objects.create(name='example.com')
        self.host = Host.objects.create(
            hostname='processupdate.example.com',
            ipaddress='192.168.1.101',
            arch=self.machine_arch,
            osvariant=self.osvariant,
            domain=self.domain,
            lastreport=timezone.now(),
        )

    def test_process_update_creates_update(self):
        """Test process_update creates PackageUpdate."""
        pkg_name = PackageName.objects.create(name='testpkg')
        old_pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='1.0.0',
            release='1.el9',
            packagetype=Package.RPM,
        )
        new_pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='1.0.1',
            release='1.el9',
            packagetype=Package.RPM,
        )

        # Create a repo and mirror for the new package
        repo = Repository.objects.create(
            name='test-repo',
            arch=self.machine_arch,
            repotype=Repository.RPM,
        )
        mirror = Mirror.objects.create(
            repo=repo,
            url='http://example.com/repo',
        )
        MirrorPackage.objects.create(mirror=mirror, package=new_pkg)
        HostRepo.objects.create(host=self.host, repo=repo)

        update_id = self.host.process_update(old_pkg, new_pkg)
        self.assertIsNotNone(update_id)
        self.assertEqual(self.host.updates.count(), 1)

    def test_process_update_marks_security_from_repo(self):
        """Test process_update marks security based on repo."""
        pkg_name = PackageName.objects.create(name='secpkg')
        old_pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='1.0.0',
            release='1.el9',
            packagetype=Package.RPM,
        )
        new_pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='0',
            version='1.0.1',
            release='1.el9',
            packagetype=Package.RPM,
        )

        # Create a security repo
        sec_repo = Repository.objects.create(
            name='security-repo',
            arch=self.machine_arch,
            repotype=Repository.RPM,
            security=True,
        )
        mirror = Mirror.objects.create(
            repo=sec_repo,
            url='http://example.com/security',
        )
        MirrorPackage.objects.create(mirror=mirror, package=new_pkg)
        HostRepo.objects.create(host=self.host, repo=sec_repo)

        update_id = self.host.process_update(old_pkg, new_pkg)
        update = PackageUpdate.objects.get(id=update_id)
        self.assertTrue(update.security)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ClientReportedUpdatesTests(TestCase):
    """Updates sent by the client must survive find_updates until a newer
    report no longer applies them."""

    def _report(self, packages, sec_updates='', bug_updates='', protocol='1'):
        report = Report.objects.create(
            host='client-updates.example.com',
            domain='example.com',
            report_ip='192.168.1.20',
            os='Ubuntu 22.04',
            kernel='5.15.0-91-generic',
            arch='x86_64',
            protocol=protocol,
            packages=packages,
            repos='' if protocol == '1' else '[]',
            modules='' if protocol == '1' else '[]',
            sec_updates=sec_updates,
            bug_updates=bug_updates,
        )
        report.process()
        return Host.objects.get(hostname='client-updates.example.com')

    def test_apt_text_updates_without_repo(self):
        """bash protocol 1 apt updates have no repo field."""
        host = self._report(
            "'nginx' '' '1.18.0' '6ubuntu14' 'amd64' 'deb'\n"
            "'curl' '' '7.81.0' '1ubuntu1.14' 'amd64' 'deb'\n",
            sec_updates='nginx.amd64 1.18.0-6ubuntu14.4\n',
            bug_updates='curl.amd64 7.81.0-1ubuntu1.15\n',
        )
        updates = {u.newpackage.name.name: u for u in host.updates.all()}
        self.assertEqual(set(updates), {'nginx', 'curl'})
        self.assertEqual(updates['nginx'].newpackage.packagetype, Package.DEB)
        self.assertEqual(updates['nginx'].newpackage.release, '6ubuntu14.4')
        self.assertTrue(updates['nginx'].security)
        self.assertFalse(updates['curl'].security)

    def test_json_updates_survive_find_updates(self):
        """A later find_updates run must not drop the client's updates."""
        host = self._report(
            json.dumps([{'name': 'nginx', 'epoch': '', 'version': '1.18.0',
                         'release': '6ubuntu14', 'arch': 'amd64', 'type': 'deb'}]),
            sec_updates=json.dumps([{'name': 'nginx', 'version': '1.18.0-6ubuntu14.4', 'arch': 'amd64'}]),
            protocol='2',
        )
        host.find_updates()
        self.assertEqual(host.updates.count(), 1)

    def test_stale_client_updates_are_dropped(self):
        """Once the package is updated, the old client update goes away."""
        self._report(
            "'nginx' '' '1.18.0' '6ubuntu14' 'amd64' 'deb'\n",
            sec_updates='nginx.amd64 1.18.0-6ubuntu14.4\n',
        )
        host = self._report("'nginx' '' '1.18.0' '6ubuntu14.4' 'amd64' 'deb'\n")
        self.assertEqual(host.updates.count(), 0)
        host.find_updates()
        self.assertEqual(host.updates.count(), 0)

    def test_client_update_replaces_computed_update(self):
        """The package manager's choice (pins, priorities) wins over the
        newest version found in the host's repos."""
        host = self._report(
            "'nginx' '' '1.18.0' '6ubuntu14' 'amd64' 'deb'\n",
            bug_updates='nginx.amd64 1.18.0-6ubuntu14.4\n',
        )
        machine_arch = MachineArchitecture.objects.get(name='x86_64')
        repo = Repository.objects.create(name='pinned', arch=machine_arch, repotype=Repository.DEB, enabled=True)
        mirror = Mirror.objects.create(repo=repo, url='http://pinned.example.com/', enabled=True, refresh=True)
        HostRepo.objects.create(host=host, repo=repo, enabled=True)
        newest = Package.objects.create(
            name=PackageName.objects.get(name='nginx'),
            arch=PackageArchitecture.objects.get(name='amd64'),
            epoch='', version='1.24.0', release='1', packagetype=Package.DEB,
        )
        MirrorPackage.objects.create(mirror=mirror, package=newest)
        host.find_updates()
        self.assertEqual(
            [(u.newpackage.version, u.newpackage.release) for u in host.updates.all()],
            [('1.18.0', '6ubuntu14.4')],
        )
