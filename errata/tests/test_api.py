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

from errata.models import Erratum
from security.models import CVE


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ErratumAPITests(APITestCase):
    """Tests for the Erratum API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        self.erratum = Erratum.objects.create(
            name='RHSA-2024:0001',
            e_type='security',
            issue_date=timezone.now(),
            synopsis='Important: openssl security update',
        )

    def test_list_errata(self):
        """Test listing all errata."""
        response = self.client.get('/api/erratum/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_erratum(self):
        """Test retrieving a single erratum."""
        response = self.client.get(f'/api/erratum/{self.erratum.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'RHSA-2024:0001')

    def test_filter_errata_by_type(self):
        """Test filtering errata by type."""
        Erratum.objects.create(
            name='RHBA-2024:0002',
            e_type='bugfix',
            issue_date=timezone.now(),
            synopsis='Bug fix update',
        )
        response = self.client.get('/api/erratum/', {'e_type': 'security'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ErratumModelTests(TestCase):
    """Tests for the Erratum model."""

    def test_erratum_creation(self):
        """Test creating an erratum."""
        erratum = Erratum.objects.create(
            name='RHSA-2024:1234',
            e_type='security',
            issue_date=timezone.now(),
            synopsis='Critical: kernel security update',
        )
        self.assertEqual(erratum.name, 'RHSA-2024:1234')
        self.assertEqual(erratum.e_type, 'security')

    def test_erratum_string_representation(self):
        """Test Erratum __str__ method."""
        erratum = Erratum.objects.create(
            name='RHSA-2024:1234',
            e_type='security',
            issue_date=timezone.now(),
            synopsis='Critical: kernel security update',
        )
        str_repr = str(erratum)
        self.assertIn('RHSA-2024:1234', str_repr)
        self.assertIn('security', str_repr)

    def test_erratum_unique_name(self):
        """Test that erratum names must be unique."""
        Erratum.objects.create(
            name='RHSA-2024:1234',
            e_type='security',
            issue_date=timezone.now(),
            synopsis='Test erratum',
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Erratum.objects.create(
                name='RHSA-2024:1234',
                e_type='bugfix',
                issue_date=timezone.now(),
                synopsis='Duplicate erratum',
            )

    def test_erratum_get_absolute_url(self):
        """Test Erratum.get_absolute_url()."""
        erratum = Erratum.objects.create(
            name='RHSA-2024:1234',
            e_type='security',
            issue_date=timezone.now(),
            synopsis='Test erratum',
        )
        url = erratum.get_absolute_url()
        self.assertIn('RHSA-2024:1234', url)

    def test_erratum_with_cves(self):
        """Test erratum with associated CVEs."""
        erratum = Erratum.objects.create(
            name='RHSA-2024:1234',
            e_type='security',
            issue_date=timezone.now(),
            synopsis='Test erratum',
        )
        cve1 = CVE.objects.create(cve_id='CVE-2024-0001')
        cve2 = CVE.objects.create(cve_id='CVE-2024-0002')
        erratum.cves.add(cve1, cve2)
        self.assertEqual(erratum.cves.count(), 2)

    def test_erratum_types(self):
        """Test different erratum types."""
        security = Erratum.objects.create(
            name='RHSA-2024:0001',
            e_type='security',
            issue_date=timezone.now(),
            synopsis='Security update',
        )
        bugfix = Erratum.objects.create(
            name='RHBA-2024:0001',
            e_type='bugfix',
            issue_date=timezone.now(),
            synopsis='Bug fix update',
        )
        enhancement = Erratum.objects.create(
            name='RHEA-2024:0001',
            e_type='enhancement',
            issue_date=timezone.now(),
            synopsis='Enhancement update',
        )
        self.assertEqual(security.e_type, 'security')
        self.assertEqual(bugfix.e_type, 'bugfix')
        self.assertEqual(enhancement.e_type, 'enhancement')
