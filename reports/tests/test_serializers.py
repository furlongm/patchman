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

from reports.serializers import (
    PackageSerializer, ReportUploadSerializer, RepoSerializer,
    UpdateSerializer,
)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ReportUploadSerializerValidationTests(TestCase):
    """Tests for ReportUploadSerializer validation."""

    def test_valid_minimal_report(self):
        """Test valid report with minimal required fields."""
        data = {
            'hostname': 'test.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
        }
        serializer = ReportUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_full_report(self):
        """Test valid report with all fields."""
        data = {
            'hostname': 'test.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
            'protocol': 2,
            'tags': ['web', 'production'],
            'reboot_required': False,
            'packages': [
                {'name': 'nginx', 'version': '1.18.0', 'arch': 'amd64', 'type': 'deb'},
            ],
            'repos': [],
            'modules': [],
            'sec_updates': [],
            'bug_updates': [],
        }
        serializer = ReportUploadSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_hostname(self):
        """Test validation fails without hostname."""
        data = {
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
        }
        serializer = ReportUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('hostname', serializer.errors)

    def test_missing_arch(self):
        """Test validation fails without arch."""
        data = {
            'hostname': 'test.example.com',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
        }
        serializer = ReportUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('arch', serializer.errors)

    def test_missing_os(self):
        """Test validation fails without os."""
        data = {
            'hostname': 'test.example.com',
            'arch': 'x86_64',
            'kernel': '5.15.0-91-generic',
        }
        serializer = ReportUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('os', serializer.errors)

    def test_missing_kernel(self):
        """Test validation fails without kernel."""
        data = {
            'hostname': 'test.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
        }
        serializer = ReportUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('kernel', serializer.errors)

    def test_empty_hostname(self):
        """Test validation fails with empty hostname."""
        data = {
            'hostname': '',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
        }
        serializer = ReportUploadSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('hostname', serializer.errors)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class PackageSerializerValidationTests(TestCase):
    """Tests for PackageSerializer validation."""

    def test_valid_package(self):
        """Test valid package data."""
        data = {
            'name': 'nginx',
            'version': '1.18.0',
            'arch': 'amd64',
            'type': 'deb',
        }
        serializer = PackageSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_package_with_optional_fields(self):
        """Test valid package with all optional fields."""
        data = {
            'name': 'nginx',
            'epoch': '1',
            'version': '1.18.0',
            'release': '6ubuntu14',
            'arch': 'amd64',
            'type': 'deb',
        }
        serializer = PackageSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_name(self):
        """Test validation fails without name."""
        data = {
            'version': '1.18.0',
            'arch': 'amd64',
        }
        serializer = PackageSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_missing_version(self):
        """Test validation fails without version."""
        data = {
            'name': 'nginx',
            'arch': 'amd64',
        }
        serializer = PackageSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('version', serializer.errors)

    def test_missing_arch(self):
        """Test validation fails without arch."""
        data = {
            'name': 'nginx',
            'version': '1.18.0',
        }
        serializer = PackageSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('arch', serializer.errors)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class RepoSerializerValidationTests(TestCase):
    """Tests for RepoSerializer validation."""

    def test_valid_repo(self):
        """Test valid repo data."""
        data = {
            'type': 'deb',
            'name': 'Ubuntu Main',
            'urls': ['http://archive.ubuntu.com/ubuntu'],
        }
        serializer = RepoSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_repo_with_optional_fields(self):
        """Test valid repo with all optional fields."""
        data = {
            'type': 'deb',
            'name': 'Ubuntu Main',
            'id': 'ubuntu-main',
            'priority': 500,
            'urls': ['http://archive.ubuntu.com/ubuntu'],
        }
        serializer = RepoSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_type(self):
        """Test validation fails without type."""
        data = {
            'name': 'Ubuntu Main',
            'urls': ['http://archive.ubuntu.com/ubuntu'],
        }
        serializer = RepoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('type', serializer.errors)

    def test_missing_urls(self):
        """Test validation passes without urls (urls is optional)."""
        data = {
            'type': 'deb',
            'name': 'Ubuntu Main',
        }
        serializer = RepoSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        # urls defaults to empty list
        self.assertEqual(serializer.validated_data['urls'], [])


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class UpdateSerializerValidationTests(TestCase):
    """Tests for UpdateSerializer validation."""

    def test_valid_update(self):
        """Test valid update data."""
        data = {
            'name': 'openssl',
            'version': '3.0.1-1',
            'arch': 'amd64',
        }
        serializer = UpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_update_with_repo(self):
        """Test valid update with repo field."""
        data = {
            'name': 'openssl',
            'version': '3.0.1-1',
            'arch': 'amd64',
            'repo': 'ubuntu-security',
        }
        serializer = UpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_name(self):
        """Test validation fails without name."""
        data = {
            'version': '3.0.1-1',
            'arch': 'amd64',
        }
        serializer = UpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_missing_version(self):
        """Test validation fails without version."""
        data = {
            'name': 'openssl',
            'arch': 'amd64',
        }
        serializer = UpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('version', serializer.errors)

    def test_missing_arch(self):
        """Test validation fails without arch."""
        data = {
            'name': 'openssl',
            'version': '3.0.1-1',
        }
        serializer = UpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('arch', serializer.errors)
