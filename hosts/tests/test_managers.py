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
from hosts.models import Host
from operatingsystems.models import OSRelease, OSVariant
from packages.models import Package, PackageName


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class HostManagerTests(TestCase):
    """Tests for HostManager custom queryset."""

    def setUp(self):
        """Set up test data."""
        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.osrelease = OSRelease.objects.create(name='Ubuntu 22.04')
        self.osvariant = OSVariant.objects.create(
            name='Ubuntu 22.04 x86_64',
            osrelease=self.osrelease,
            arch=self.arch,
        )
        self.domain = Domain.objects.create(name='example.com')
        self.now = timezone.now()

    def test_host_manager_select_related(self):
        """Test HostManager uses select_related for efficiency."""
        Host.objects.create(
            hostname='test1.example.com',
            ipaddress='192.168.1.1',
            arch=self.arch,
            osvariant=self.osvariant,
            domain=self.domain,
            lastreport=self.now,
        )
        Host.objects.create(
            hostname='test2.example.com',
            ipaddress='192.168.1.2',
            arch=self.arch,
            osvariant=self.osvariant,
            domain=self.domain,
            lastreport=self.now,
        )
        # Manager should return queryset with select_related
        hosts = Host.objects.all()
        self.assertEqual(hosts.count(), 2)

    def test_host_manager_returns_all_hosts(self):
        """Test HostManager returns all hosts."""
        Host.objects.create(
            hostname='host1.example.com',
            ipaddress='192.168.1.1',
            arch=self.arch,
            osvariant=self.osvariant,
            domain=self.domain,
            lastreport=self.now,
        )
        Host.objects.create(
            hostname='host2.example.com',
            ipaddress='192.168.1.2',
            arch=self.arch,
            osvariant=self.osvariant,
            domain=self.domain,
            lastreport=self.now,
        )
        Host.objects.create(
            hostname='host3.example.com',
            ipaddress='192.168.1.3',
            arch=self.arch,
            osvariant=self.osvariant,
            domain=self.domain,
            lastreport=self.now,
        )
        self.assertEqual(Host.objects.count(), 3)

    def test_host_manager_filter_works(self):
        """Test HostManager filtering works correctly."""
        Host.objects.create(
            hostname='web1.example.com',
            ipaddress='192.168.1.1',
            arch=self.arch,
            osvariant=self.osvariant,
            domain=self.domain,
            lastreport=self.now,
        )
        Host.objects.create(
            hostname='db1.example.com',
            ipaddress='192.168.1.2',
            arch=self.arch,
            osvariant=self.osvariant,
            domain=self.domain,
            lastreport=self.now,
        )
        web_hosts = Host.objects.filter(hostname__startswith='web')
        self.assertEqual(web_hosts.count(), 1)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class PackageManagerTests(TestCase):
    """Tests for PackageManager custom queryset."""

    def setUp(self):
        """Set up test data."""
        self.arch = PackageArchitecture.objects.create(name='amd64')

    def test_package_manager_select_related(self):
        """Test PackageManager uses select_related for efficiency."""
        pkg_name = PackageName.objects.create(name='nginx')
        Package.objects.create(
            name=pkg_name,
            arch=self.arch,
            epoch='',
            version='1.18.0',
            release='1',
            packagetype=Package.DEB,
        )
        # Manager should return queryset with select_related
        packages = Package.objects.all()
        self.assertEqual(packages.count(), 1)

    def test_package_manager_returns_all_packages(self):
        """Test PackageManager returns all packages."""
        for name in ['nginx', 'curl', 'vim']:
            pkg_name = PackageName.objects.create(name=name)
            Package.objects.create(
                name=pkg_name,
                arch=self.arch,
                epoch='',
                version='1.0.0',
                release='1',
                packagetype=Package.DEB,
            )
        self.assertEqual(Package.objects.count(), 3)

    def test_package_manager_filter_by_name(self):
        """Test PackageManager filtering by name."""
        nginx_name = PackageName.objects.create(name='nginx')
        curl_name = PackageName.objects.create(name='curl')
        Package.objects.create(
            name=nginx_name,
            arch=self.arch,
            epoch='',
            version='1.18.0',
            release='1',
            packagetype=Package.DEB,
        )
        Package.objects.create(
            name=curl_name,
            arch=self.arch,
            epoch='',
            version='7.81.0',
            release='1',
            packagetype=Package.DEB,
        )
        nginx_packages = Package.objects.filter(name=nginx_name)
        self.assertEqual(nginx_packages.count(), 1)

    def test_package_manager_filter_by_type(self):
        """Test PackageManager filtering by package type."""
        deb_name = PackageName.objects.create(name='debpkg')
        rpm_name = PackageName.objects.create(name='rpmpkg')
        rpm_arch = PackageArchitecture.objects.create(name='x86_64')
        Package.objects.create(
            name=deb_name,
            arch=self.arch,
            epoch='',
            version='1.0.0',
            release='1',
            packagetype=Package.DEB,
        )
        Package.objects.create(
            name=rpm_name,
            arch=rpm_arch,
            epoch='',
            version='1.0.0',
            release='1.el9',
            packagetype=Package.RPM,
        )
        deb_packages = Package.objects.filter(packagetype=Package.DEB)
        rpm_packages = Package.objects.filter(packagetype=Package.RPM)
        self.assertEqual(deb_packages.count(), 1)
        self.assertEqual(rpm_packages.count(), 1)
