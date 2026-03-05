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

from domains.models import Domain


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class DomainAPITests(APITestCase):
    """Tests for the Domain API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser', password='testpass'
        )
        self.client.force_authenticate(user=self.user)
        self.domain = Domain.objects.create(name='example.com')

    def test_list_domains(self):
        """Test listing all domains."""
        response = self.client.get('/api/domain/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_domain(self):
        """Test retrieving a single domain."""
        response = self.client.get(f'/api/domain/{self.domain.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'example.com')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class DomainModelTests(TestCase):
    """Tests for the Domain model."""

    def test_domain_creation(self):
        """Test creating a domain."""
        domain = Domain.objects.create(name='test.example.com')
        self.assertEqual(domain.name, 'test.example.com')

    def test_domain_string_representation(self):
        """Test Domain __str__ method."""
        domain = Domain.objects.create(name='prod.example.com')
        self.assertEqual(str(domain), 'prod.example.com')

    def test_domain_unique_name(self):
        """Test that domain names must be unique."""
        Domain.objects.create(name='unique.example.com')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Domain.objects.create(name='unique.example.com')

    def test_extract_domain_from_fqdn(self):
        """Test extracting domain from fully qualified domain name."""
        # Domain extraction is done elsewhere, but test the model can store it
        fqdn = 'server1.prod.example.com'
        domain_name = '.'.join(fqdn.split('.')[1:])  # prod.example.com
        domain = Domain.objects.create(name=domain_name)
        self.assertEqual(domain.name, 'prod.example.com')
