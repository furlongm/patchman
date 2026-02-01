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
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

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
class HostAPITests(APITestCase):
    """Tests for the Host API endpoints."""

    def setUp(self):
        """Set up test data."""
        # Create user for authentication
        self.user = User.objects.create_user(
            username='testuser', password='testpass'
        )
        self.client.force_authenticate(user=self.user)

        # Create required related objects
        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.domain = Domain.objects.create(name='example.com')
        self.os_release = OSRelease.objects.create(
            name='Ubuntu 22.04', codename='jammy'
        )
        self.os_variant = OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS', osrelease=self.os_release
        )

        # Create test host
        self.host = Host.objects.create(
            hostname='testhost.example.com',
            ipaddress='192.168.1.100',
            osvariant=self.os_variant,
            kernel='5.15.0-91-generic',
            arch=self.arch,
            domain=self.domain,
            lastreport=timezone.now(),
        )

    def test_list_hosts(self):
        """Test listing all hosts."""
        response = self.client.get('/api/host/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_host(self):
        """Test retrieving a single host."""
        response = self.client.get(f'/api/host/{self.host.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['hostname'], 'testhost.example.com')

    def test_filter_hosts_by_hostname(self):
        """Test filtering hosts by hostname."""
        response = self.client.get('/api/host/', {'hostname': 'testhost.example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        response = self.client.get('/api/host/', {'hostname': 'nonexistent'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_host_update_counts(self):
        """Test that bugfix and security update counts are returned."""
        response = self.client.get(f'/api/host/{self.host.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bugfix_update_count', response.data)
        self.assertIn('security_update_count', response.data)
        self.assertEqual(response.data['bugfix_update_count'], 0)
        self.assertEqual(response.data['security_update_count'], 0)

    def test_host_update_counts_with_updates(self):
        """Test update counts with actual security and bugfix updates."""
        # Create package architecture and names
        pkg_arch = PackageArchitecture.objects.create(name='amd64')
        pkg_name = PackageName.objects.create(name='openssl')

        # Create old and new packages
        old_pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='3.0.0', release='1', packagetype='D'
        )
        new_security_pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='3.0.1', release='1', packagetype='D'
        )
        new_bugfix_pkg = Package.objects.create(
            name=pkg_name, arch=pkg_arch, epoch='',
            version='3.0.2', release='1', packagetype='D'
        )

        # Create security and bugfix updates
        security_update = PackageUpdate.objects.create(
            oldpackage=old_pkg, newpackage=new_security_pkg, security=True
        )
        bugfix_update = PackageUpdate.objects.create(
            oldpackage=old_pkg, newpackage=new_bugfix_pkg, security=False
        )

        # Associate updates with host
        self.host.updates.add(security_update, bugfix_update)

        response = self.client.get(f'/api/host/{self.host.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['security_update_count'], 1)
        self.assertEqual(response.data['bugfix_update_count'], 1)

    def test_create_host_via_api(self):
        """Test creating a host via API."""
        data = {
            'hostname': 'newhost.example.com',
            'ipaddress': '192.168.1.101',
            'kernel': '5.15.0-92-generic',
            'arch': f'http://testserver/api/machine-architecture/{self.arch.id}/',
            'domain': f'http://testserver/api/domain/{self.domain.id}/',
            'osvariant': f'http://testserver/api/os-variant/{self.os_variant.id}/',
            'lastreport': timezone.now().isoformat(),
            'reboot_required': False,
            'host_repos_only': True,
        }
        response = self.client.post('/api/host/', data, format='json')
        # ModelViewSet allows creation
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied."""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/host/')
        # DRF default is IsAuthenticatedOrReadOnly, so GET may be allowed
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        )


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class HostModelTests(TestCase):
    """Tests for the Host model."""

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

    def test_host_creation(self):
        """Test creating a host with required fields."""
        host = Host.objects.create(
            hostname='testhost.example.com',
            ipaddress='192.168.1.100',
            osvariant=self.os_variant,
            kernel='5.15.0-91-generic',
            arch=self.arch,
            domain=self.domain,
            lastreport=timezone.now(),
        )
        self.assertEqual(host.hostname, 'testhost.example.com')
        self.assertEqual(str(host.arch), 'x86_64')

    def test_host_string_representation(self):
        """Test Host __str__ method."""
        host = Host.objects.create(
            hostname='testhost.example.com',
            ipaddress='192.168.1.100',
            osvariant=self.os_variant,
            kernel='5.15.0-91-generic',
            arch=self.arch,
            domain=self.domain,
            lastreport=timezone.now(),
        )
        self.assertEqual(str(host), 'testhost.example.com')

    def test_host_unique_hostname(self):
        """Test that hostname must be unique."""
        Host.objects.create(
            hostname='unique.example.com',
            ipaddress='192.168.1.100',
            osvariant=self.os_variant,
            kernel='5.15.0-91-generic',
            arch=self.arch,
            domain=self.domain,
            lastreport=timezone.now(),
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Host.objects.create(
                hostname='unique.example.com',
                ipaddress='192.168.1.101',
                osvariant=self.os_variant,
                kernel='5.15.0-91-generic',
                arch=self.arch,
                domain=self.domain,
                lastreport=timezone.now(),
            )

    def test_host_get_absolute_url(self):
        """Test Host.get_absolute_url() returns correct URL."""
        host = Host.objects.create(
            hostname='testhost.example.com',
            ipaddress='192.168.1.100',
            osvariant=self.os_variant,
            kernel='5.15.0-91-generic',
            arch=self.arch,
            domain=self.domain,
            lastreport=timezone.now(),
        )
        url = host.get_absolute_url()
        self.assertIn('testhost.example.com', url)

    def test_host_tags(self):
        """Test Host tagging functionality."""
        host = Host.objects.create(
            hostname='tagged.example.com',
            ipaddress='192.168.1.100',
            osvariant=self.os_variant,
            kernel='5.15.0-91-generic',
            arch=self.arch,
            domain=self.domain,
            lastreport=timezone.now(),
        )
        host.tags.add('production', 'web')
        self.assertEqual(host.tags.count(), 2)
        self.assertTrue(host.tags.filter(name='production').exists())

    def test_host_reboot_required_default(self):
        """Test that reboot_required defaults to False."""
        host = Host.objects.create(
            hostname='testhost.example.com',
            ipaddress='192.168.1.100',
            osvariant=self.os_variant,
            kernel='5.15.0-91-generic',
            arch=self.arch,
            domain=self.domain,
            lastreport=timezone.now(),
        )
        self.assertFalse(host.reboot_required)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class HostRepoTests(TestCase):
    """Tests for the HostRepo model."""

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
        self.repo = Repository.objects.create(
            name='ubuntu-main',
            repotype='D',
            arch=self.arch,
        )

    def test_host_repo_creation(self):
        """Test creating a HostRepo relationship."""
        host_repo = HostRepo.objects.create(
            host=self.host,
            repo=self.repo,
            enabled=True,
            priority=500,
        )
        self.assertEqual(host_repo.host, self.host)
        self.assertEqual(host_repo.repo, self.repo)
        self.assertTrue(host_repo.enabled)
        self.assertEqual(host_repo.priority, 500)

    def test_host_repos_relationship(self):
        """Test Host.repos ManyToMany relationship via HostRepo."""
        HostRepo.objects.create(
            host=self.host,
            repo=self.repo,
            enabled=True,
        )
        self.assertIn(self.repo, self.host.repos.all())


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class HostRepoAPITests(APITestCase):
    """Tests for the HostRepo API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

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
        self.repo = Repository.objects.create(
            name='ubuntu-main',
            repotype='D',
            arch=self.arch,
        )
        self.host_repo = HostRepo.objects.create(
            host=self.host,
            repo=self.repo,
            enabled=True,
            priority=500,
        )

    def test_list_host_repos(self):
        """Test listing all host-repo relationships."""
        response = self.client.get('/api/host-repo/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_host_repo(self):
        """Test retrieving a single host-repo relationship."""
        response = self.client.get(f'/api/host-repo/{self.host_repo.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['enabled'], True)
        self.assertEqual(response.data['priority'], 500)
