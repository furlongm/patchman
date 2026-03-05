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
from rest_framework import status
from rest_framework.test import APITestCase

from arch.models import MachineArchitecture
from operatingsystems.models import OSRelease, OSVariant


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class OSReleaseAPITests(APITestCase):
    """Tests for the OS Release API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        self.os_release = OSRelease.objects.create(
            name='Ubuntu 22.04',
            codename='jammy',
        )

    def test_list_os_releases(self):
        """Test listing all OS releases."""
        response = self.client.get('/api/os-release/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_os_release(self):
        """Test retrieving a single OS release."""
        response = self.client.get(f'/api/os-release/{self.os_release.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Ubuntu 22.04')

    def test_filter_os_releases_by_name(self):
        """Test filtering OS releases by name."""
        OSRelease.objects.create(name='Rocky Linux 9', codename='')
        response = self.client.get('/api/os-release/', {'name': 'Ubuntu 22.04'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class OSVariantAPITests(APITestCase):
    """Tests for the OS Variant API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.os_release = OSRelease.objects.create(
            name='Ubuntu 22.04',
            codename='jammy',
        )
        self.os_variant = OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS',
            arch=self.arch,
            osrelease=self.os_release,
        )

    def test_list_os_variants(self):
        """Test listing all OS variants."""
        response = self.client.get('/api/os-variant/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_os_variant(self):
        """Test retrieving a single OS variant."""
        response = self.client.get(f'/api/os-variant/{self.os_variant.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Ubuntu 22.04.3 LTS')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class OSReleaseModelTests(TestCase):
    """Tests for the OSRelease model."""

    def test_os_release_creation(self):
        """Test creating an OS release."""
        os_release = OSRelease.objects.create(
            name='Debian 12',
            codename='bookworm',
        )
        self.assertEqual(os_release.name, 'Debian 12')
        self.assertEqual(os_release.codename, 'bookworm')

    def test_os_release_string_representation(self):
        """Test OSRelease __str__ method with codename."""
        os_release = OSRelease.objects.create(
            name='Ubuntu 22.04',
            codename='jammy',
        )
        self.assertEqual(str(os_release), 'Ubuntu 22.04 (jammy)')

    def test_os_release_string_without_codename(self):
        """Test OSRelease __str__ method without codename."""
        os_release = OSRelease.objects.create(
            name='Rocky Linux 9',
            codename='',
        )
        self.assertEqual(str(os_release), 'Rocky Linux 9')

    def test_os_release_unique_name(self):
        """Test that OS release names must be unique."""
        OSRelease.objects.create(name='Ubuntu 22.04', codename='jammy')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            OSRelease.objects.create(name='Ubuntu 22.04', codename='')

    def test_os_release_get_absolute_url(self):
        """Test OSRelease.get_absolute_url()."""
        os_release = OSRelease.objects.create(name='Ubuntu 22.04', codename='jammy')
        url = os_release.get_absolute_url()
        self.assertIn(str(os_release.id), url)

    def test_os_release_with_cpe_name(self):
        """Test OS release with CPE name."""
        os_release = OSRelease.objects.create(
            name='Rocky Linux 9',
            codename='',
            cpe_name='cpe:/o:rocky:rocky:9',
        )
        self.assertEqual(os_release.cpe_name, 'cpe:/o:rocky:rocky:9')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class OSVariantModelTests(TestCase):
    """Tests for the OSVariant model."""

    def setUp(self):
        """Set up test data."""
        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.os_release = OSRelease.objects.create(
            name='Ubuntu 22.04',
            codename='jammy',
        )

    def test_os_variant_creation(self):
        """Test creating an OS variant."""
        os_variant = OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS',
            arch=self.arch,
            osrelease=self.os_release,
        )
        self.assertEqual(os_variant.name, 'Ubuntu 22.04.3 LTS')

    def test_os_variant_string_representation(self):
        """Test OSVariant __str__ method."""
        os_variant = OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS',
            arch=self.arch,
            osrelease=self.os_release,
        )
        self.assertIn('Ubuntu 22.04.3 LTS', str(os_variant))
        self.assertIn('x86_64', str(os_variant))

    def test_os_variant_unique_name(self):
        """Test that OS variant names must be unique."""
        OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS',
            arch=self.arch,
            osrelease=self.os_release,
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            OSVariant.objects.create(
                name='Ubuntu 22.04.3 LTS',
                arch=self.arch,
                osrelease=self.os_release,
            )

    def test_os_variant_get_absolute_url(self):
        """Test OSVariant.get_absolute_url()."""
        os_variant = OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS',
            arch=self.arch,
            osrelease=self.os_release,
        )
        url = os_variant.get_absolute_url()
        self.assertIn(str(os_variant.id), url)

    def test_os_variant_without_arch(self):
        """Test OS variant can be created without arch."""
        os_variant = OSVariant.objects.create(
            name='Generic Linux',
            osrelease=self.os_release,
        )
        self.assertIsNone(os_variant.arch)

    def test_os_variant_without_osrelease(self):
        """Test OS variant can be created without osrelease."""
        os_variant = OSVariant.objects.create(
            name='Unknown OS',
            arch=self.arch,
        )
        self.assertIsNone(os_variant.osrelease)
