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

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rest_framework_api_key.models import APIKey


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class CreateApiKeyCommandTests(TestCase):
    """Tests for create_api_key management command."""

    def test_create_api_key_creates_key(self):
        """Test create_api_key creates a new API key."""
        out = StringIO()
        call_command('create_api_key', 'test-client', stdout=out)

        # Key should be created
        self.assertEqual(APIKey.objects.count(), 1)
        api_key = APIKey.objects.first()
        self.assertEqual(api_key.name, 'test-client')

    def test_create_api_key_outputs_key(self):
        """Test create_api_key outputs the generated key."""
        out = StringIO()
        call_command('create_api_key', 'output-test', stdout=out)

        output = out.getvalue()
        self.assertIn('output-test', output)
        self.assertIn('Key:', output)
        self.assertIn('api_key=', output)

    def test_create_api_key_multiple_keys(self):
        """Test creating multiple API keys."""
        call_command('create_api_key', 'client1', stdout=StringIO())
        call_command('create_api_key', 'client2', stdout=StringIO())
        call_command('create_api_key', 'client3', stdout=StringIO())

        self.assertEqual(APIKey.objects.count(), 3)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ListApiKeysCommandTests(TestCase):
    """Tests for list_api_keys management command."""

    def test_list_api_keys_empty(self):
        """Test list_api_keys with no keys."""
        out = StringIO()
        call_command('list_api_keys', stdout=out)

        output = out.getvalue()
        self.assertIn('No API keys found', output)

    def test_list_api_keys_shows_keys(self):
        """Test list_api_keys shows created keys."""
        APIKey.objects.create_key(name='test-key-1')
        APIKey.objects.create_key(name='test-key-2')

        out = StringIO()
        call_command('list_api_keys', stdout=out)

        output = out.getvalue()
        self.assertIn('test-key-1', output)
        self.assertIn('test-key-2', output)
        self.assertIn('Total: 2', output)

    def test_list_api_keys_hides_revoked(self):
        """Test list_api_keys hides revoked keys by default."""
        api_key, _ = APIKey.objects.create_key(name='active-key')
        revoked_key, _ = APIKey.objects.create_key(name='revoked-key')
        revoked_key.revoked = True
        revoked_key.save()

        out = StringIO()
        call_command('list_api_keys', stdout=out)

        output = out.getvalue()
        self.assertIn('active-key', output)
        self.assertNotIn('revoked-key', output)
        self.assertIn('Total: 1', output)

    def test_list_api_keys_all_shows_revoked(self):
        """Test list_api_keys --all shows revoked keys."""
        api_key, _ = APIKey.objects.create_key(name='active-key')
        revoked_key, _ = APIKey.objects.create_key(name='revoked-key')
        revoked_key.revoked = True
        revoked_key.save()

        out = StringIO()
        call_command('list_api_keys', '--all', stdout=out)

        output = out.getvalue()
        self.assertIn('active-key', output)
        self.assertIn('revoked-key', output)
        self.assertIn('Total: 2', output)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class RevokeApiKeyCommandTests(TestCase):
    """Tests for revoke_api_key management command."""

    def test_revoke_api_key_by_name(self):
        """Test revoking API key by name."""
        api_key, _ = APIKey.objects.create_key(name='revoke-test')

        out = StringIO()
        call_command('revoke_api_key', 'revoke-test', stdout=out)

        api_key.refresh_from_db()
        self.assertTrue(api_key.revoked)

    def test_revoke_api_key_by_prefix(self):
        """Test revoking API key by prefix."""
        api_key, _ = APIKey.objects.create_key(name='prefix-test')
        prefix = api_key.prefix

        out = StringIO()
        call_command('revoke_api_key', prefix, stdout=out)

        api_key.refresh_from_db()
        self.assertTrue(api_key.revoked)

    def test_revoke_api_key_not_found(self):
        """Test revoking non-existent key raises error."""
        with self.assertRaises(CommandError) as context:
            call_command('revoke_api_key', 'nonexistent')

        self.assertIn('No API key found', str(context.exception))

    def test_revoke_api_key_already_revoked(self):
        """Test revoking already revoked key shows warning."""
        api_key, _ = APIKey.objects.create_key(name='already-revoked')
        api_key.revoked = True
        api_key.save()

        out = StringIO()
        call_command('revoke_api_key', 'already-revoked', stdout=out)

        output = out.getvalue()
        self.assertIn('already revoked', output)

    def test_revoke_api_key_delete(self):
        """Test --delete permanently removes the key."""
        api_key, _ = APIKey.objects.create_key(name='delete-test')

        out = StringIO()
        call_command('revoke_api_key', 'delete-test', '--delete', stdout=out)

        self.assertEqual(APIKey.objects.filter(name='delete-test').count(), 0)
        output = out.getvalue()
        self.assertIn('Permanently deleted', output)
