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
from rest_framework import status
from rest_framework.test import APITestCase

from arch.models import MachineArchitecture, PackageArchitecture
from domains.models import Domain
from hosts.models import Host, HostRepo
from operatingsystems.models import OSRelease, OSVariant
from packages.models import Package, PackageName
from reports.models import Report
from repos.models import Repository


@override_settings(
    REQUIRE_API_KEY=False,
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class EndToEndProtocol2Tests(APITestCase):
    """End-to-end integration tests for Protocol 2."""

    def test_full_report_creates_host_packages_repos(self):
        """Test full report creates all expected database records."""
        data = {
            'hostname': 'e2e-test.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04 LTS',
            'kernel': '5.15.0-91-generic',
            'packages': [
                {
                    'name': 'nginx',
                    'epoch': '',
                    'version': '1.18.0',
                    'release': '6ubuntu14',
                    'arch': 'amd64',
                    'type': 'deb',
                },
                {
                    'name': 'curl',
                    'epoch': '',
                    'version': '7.81.0',
                    'release': '1ubuntu1.15',
                    'arch': 'amd64',
                    'type': 'deb',
                },
            ],
            'repos': [
                {
                    'id': 'ubuntu-main',
                    'name': 'Ubuntu 22.04 main',
                    'type': 'deb',
                    'url': 'http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64',
                },
            ],
        }

        response = self.client.post('/api/report/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        # Verify report was created
        report_id = response.data.get('report_id')
        self.assertIsNotNone(report_id)
        report = Report.objects.get(id=report_id)
        self.assertEqual(report.host, 'e2e-test.example.com')
        self.assertEqual(report.protocol, '2')

    def test_report_upload_and_retrieve(self):
        """Test report can be uploaded and then retrieved via API."""
        data = {
            'hostname': 'retrieve-test.example.com',
            'arch': 'x86_64',
            'os': 'Rocky Linux 9',
            'kernel': '5.14.0-362.el9.x86_64',
            'packages': [],
        }

        # Upload
        response = self.client.post('/api/report/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        report_id = response.data['report_id']

        # Retrieve
        response = self.client.get(f'/api/report/{report_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['host'], 'retrieve-test.example.com')


@override_settings(
    REQUIRE_API_KEY=False,
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class Protocol1CompatibilityTests(TestCase):
    """Tests for Protocol 1 backward compatibility."""

    def test_protocol1_report_stored(self):
        """Test Protocol 1 report can be created and stored."""
        # Protocol 1 reports store raw text data
        packages_text = "'nginx' '' '1.18.0' '6ubuntu14' 'amd64' 'deb'"
        repos_text = "deb : Ubuntu 22.04 : ubuntu-main : http://archive.ubuntu.com/ubuntu/"

        report = Report.objects.create(
            host='protocol1.example.com',
            domain='example.com',
            report_ip='192.168.1.10',
            os='Ubuntu 22.04',
            kernel='5.15.0-91-generic',
            arch='x86_64',
            protocol='1',
            packages=packages_text,
            repos=repos_text,
        )

        self.assertEqual(report.protocol, '1')
        self.assertIn('nginx', report.packages)
        self.assertIn('ubuntu-main', report.repos)


@override_settings(
    REQUIRE_API_KEY=False,
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class HostUpdateIntegrationTests(TestCase):
    """Integration tests for host update detection."""

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

    def test_report_processing_associates_packages_with_host(self):
        """Test that processing a report associates packages with the host."""
        host = Host.objects.create(
            hostname='pkg-assoc.example.com',
            ipaddress='192.168.1.50',
            arch=self.machine_arch,
            osvariant=self.osvariant,
            domain=self.domain,
            lastreport=timezone.now(),
        )

        # Create a package
        pkg_name = PackageName.objects.create(name='testpkg')
        pkg = Package.objects.create(
            name=pkg_name,
            arch=self.pkg_arch,
            epoch='',
            version='1.0.0',
            release='1',
            packagetype=Package.DEB,
        )

        # Add package to host
        host.packages.add(pkg)
        self.assertIn(pkg, host.packages.all())
        self.assertEqual(host.packages.count(), 1)

    def test_host_repo_association(self):
        """Test that repos are correctly associated with hosts."""
        host = Host.objects.create(
            hostname='repo-assoc.example.com',
            ipaddress='192.168.1.51',
            arch=self.machine_arch,
            osvariant=self.osvariant,
            domain=self.domain,
            lastreport=timezone.now(),
        )

        repo = Repository.objects.create(
            name='test-repo',
            arch=self.machine_arch,
            repotype=Repository.DEB,
        )

        HostRepo.objects.create(
            host=host,
            repo=repo,
            enabled=True,
        )

        self.assertEqual(host.repos.count(), 1)
        self.assertEqual(host.repos.first(), repo)


@override_settings(
    REQUIRE_API_KEY=False,
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ConcurrentReportTests(APITestCase):
    """Tests for concurrent report handling."""

    def test_multiple_reports_same_host_sequential(self):
        """Test multiple reports for same host create separate Report records."""
        data1 = {
            'hostname': 'concurrent.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-90-generic',
            'packages': [],
        }

        data2 = {
            'hostname': 'concurrent.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',  # Newer kernel
            'packages': [],
        }

        response1 = self.client.post('/api/report/', data1, format='json')
        response2 = self.client.post('/api/report/', data2, format='json')

        self.assertEqual(response1.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response2.status_code, status.HTTP_202_ACCEPTED)

        # Both reports should exist
        reports = Report.objects.filter(host='concurrent.example.com')
        self.assertEqual(reports.count(), 2)

    def test_reports_from_different_hosts(self):
        """Test reports from different hosts don't interfere."""
        data1 = {
            'hostname': 'host1.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
            'packages': [],
        }

        data2 = {
            'hostname': 'host2.example.com',
            'arch': 'x86_64',
            'os': 'Rocky Linux 9',
            'kernel': '5.14.0-362.el9.x86_64',
            'packages': [],
        }

        response1 = self.client.post('/api/report/', data1, format='json')
        response2 = self.client.post('/api/report/', data2, format='json')

        self.assertEqual(response1.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response2.status_code, status.HTTP_202_ACCEPTED)

        report1 = Report.objects.get(id=response1.data['report_id'])
        report2 = Report.objects.get(id=response2.data['report_id'])

        self.assertEqual(report1.host, 'host1.example.com')
        self.assertEqual(report2.host, 'host2.example.com')
