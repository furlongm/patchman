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

from security.models import CVE, CWE, Reference


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class SecurityAPITests(APITestCase):
    """Tests for the Security API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser', password='testpass'
        )
        self.client.force_authenticate(user=self.user)

        self.cve = CVE.objects.create(
            cve_id='CVE-2024-1234',
            description='Test vulnerability',
        )
        self.reference = Reference.objects.create(
            ref_type='ADVISORY',
            url='https://example.com/advisory/CVE-2024-1234',
        )
        self.cwe = CWE.objects.create(
            cwe_id='CWE-79',
            name='Cross-site Scripting',
        )

    def test_list_cves(self):
        """Test listing all CVEs."""
        response = self.client.get('/api/cve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_cve(self):
        """Test retrieving a single CVE."""
        response = self.client.get(f'/api/cve/{self.cve.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['cve_id'], 'CVE-2024-1234')

    def test_list_references(self):
        """Test listing references."""
        response = self.client.get('/api/reference/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_reference(self):
        """Test retrieving a single reference."""
        response = self.client.get(f'/api/reference/{self.reference.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ref_type'], 'ADVISORY')

    def test_list_cwes(self):
        """Test listing CWEs."""
        response = self.client.get('/api/cwe/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_cwe(self):
        """Test retrieving a single CWE."""
        response = self.client.get(f'/api/cwe/{self.cwe.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['cwe_id'], 'CWE-79')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class CVEModelTests(TestCase):
    """Tests for the CVE model."""

    def test_cve_creation(self):
        """Test creating a CVE."""
        cve = CVE.objects.create(
            cve_id='CVE-2024-5678',
            description='Remote code execution vulnerability',
        )
        self.assertEqual(cve.cve_id, 'CVE-2024-5678')

    def test_cve_string_representation(self):
        """Test CVE __str__ method."""
        cve = CVE.objects.create(
            cve_id='CVE-2024-9999',
            description='Buffer overflow',
        )
        self.assertEqual(str(cve), 'CVE-2024-9999')

    def test_cve_unique_id(self):
        """Test that CVE IDs must be unique."""
        CVE.objects.create(cve_id='CVE-2024-0001')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            CVE.objects.create(cve_id='CVE-2024-0001')

    def test_cve_get_absolute_url(self):
        """Test CVE.get_absolute_url()."""
        cve = CVE.objects.create(cve_id='CVE-2024-1111')
        url = cve.get_absolute_url()
        self.assertIn('CVE-2024-1111', url)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class CWEModelTests(TestCase):
    """Tests for the CWE model."""

    def test_cwe_creation(self):
        """Test creating a CWE."""
        cwe = CWE.objects.create(
            cwe_id='CWE-79',
            name='Improper Neutralization of Input During Web Page Generation',
        )
        self.assertEqual(cwe.cwe_id, 'CWE-79')

    def test_cwe_string_representation(self):
        """Test CWE __str__ method."""
        cwe = CWE.objects.create(
            cwe_id='CWE-89',
            name='SQL Injection',
        )
        str_rep = str(cwe)
        self.assertIn('CWE-89', str_rep)
        self.assertIn('SQL Injection', str_rep)

    def test_cwe_unique_id(self):
        """Test that CWE IDs must be unique."""
        CWE.objects.create(cwe_id='CWE-100')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            CWE.objects.create(cwe_id='CWE-100')

    def test_cwe_int_id_property(self):
        """Test CWE.int_id property extracts numeric part."""
        cwe = CWE.objects.create(cwe_id='CWE-787')
        self.assertEqual(cwe.int_id, 787)

    def test_cwe_get_absolute_url(self):
        """Test CWE.get_absolute_url()."""
        cwe = CWE.objects.create(cwe_id='CWE-20')
        url = cwe.get_absolute_url()
        self.assertIn('CWE-20', url)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ReferenceModelTests(TestCase):
    """Tests for the Reference model."""

    def test_reference_creation(self):
        """Test creating a reference."""
        ref = Reference.objects.create(
            ref_type='VENDOR',
            url='https://vendor.com/security/advisory',
        )
        self.assertEqual(ref.ref_type, 'VENDOR')

    def test_reference_string_representation(self):
        """Test Reference __str__ method."""
        ref = Reference.objects.create(
            ref_type='ADVISORY',
            url='https://example.com/advisory',
        )
        self.assertEqual(str(ref), 'https://example.com/advisory')

    def test_reference_unique_together(self):
        """Test that ref_type + url must be unique together."""
        Reference.objects.create(
            ref_type='PATCH',
            url='https://example.com/patch',
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Reference.objects.create(
                ref_type='PATCH',
                url='https://example.com/patch',
            )

    def test_reference_same_url_different_type(self):
        """Test that same URL with different type is allowed."""
        Reference.objects.create(
            ref_type='ADVISORY',
            url='https://example.com/security',
        )
        # Same URL, different type should work
        ref2 = Reference.objects.create(
            ref_type='VENDOR',
            url='https://example.com/security',
        )
        self.assertEqual(ref2.ref_type, 'VENDOR')
