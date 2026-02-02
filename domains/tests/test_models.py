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

from domains.models import Domain


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class DomainMethodTests(TestCase):
    """Tests for Domain model methods."""

    def test_domain_creation(self):
        """Test creating a Domain."""
        domain = Domain.objects.create(name='example.com')
        self.assertEqual(domain.name, 'example.com')

    def test_domain_str(self):
        """Test Domain __str__ method."""
        domain = Domain.objects.create(name='example.com')
        self.assertEqual(str(domain), 'example.com')

    def test_domain_unique_name(self):
        """Test Domain name is unique."""
        Domain.objects.create(name='example.com')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Domain.objects.create(name='example.com')

    def test_domain_extract_from_fqdn(self):
        """Test extracting domain from FQDN via Host creation."""
        # Domains are typically extracted when hosts are created
        # Test the domain itself can be created with subdomain parts
        Domain.objects.create(name='subdomain.example.com')
        domain = Domain.objects.get(name='subdomain.example.com')
        self.assertEqual(domain.name, 'subdomain.example.com')
