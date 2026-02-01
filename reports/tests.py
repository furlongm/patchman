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
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_api_key.models import APIKey

from reports.models import Report


@override_settings(
    REQUIRE_API_KEY=False,
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ReportAPITests(APITestCase):
    """Tests for the Protocol 2 JSON report API."""

    def setUp(self):
        self.url = '/api/report/'

    def test_upload_minimal_report(self):
        """Test uploading a minimal valid report."""
        data = {
            'protocol': 2,
            'hostname': 'testhost.example.com',
            'arch': 'x86_64',
            'kernel': '5.15.0-91-generic',
            'os': 'Ubuntu 22.04.3 LTS',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['status'], 'accepted')
        self.assertIn('report_id', response.data)

        # Verify report was created
        report = Report.objects.get(id=response.data['report_id'])
        self.assertEqual(report.host, 'testhost.example.com')
        self.assertEqual(report.protocol, '2')

    def test_upload_full_report(self):
        """Test uploading a report with all fields."""
        data = {
            'protocol': 2,
            'hostname': 'server1.example.com',
            'arch': 'x86_64',
            'kernel': '5.15.0-91-generic',
            'os': 'Ubuntu 22.04.3 LTS',
            'tags': ['web', 'production'],
            'reboot_required': True,
            'packages': [
                {
                    'name': 'nginx',
                    'epoch': '',
                    'version': '1.18.0',
                    'release': '6ubuntu14',
                    'arch': 'amd64',
                    'type': 'deb'
                },
                {
                    'name': 'curl',
                    'epoch': '',
                    'version': '7.81.0',
                    'release': '1ubuntu1.15',
                    'arch': 'amd64',
                    'type': 'deb'
                }
            ],
            'repos': [
                {
                    'type': 'deb',
                    'name': 'Ubuntu 22.04 amd64 main',
                    'id': 'ubuntu-main',
                    'priority': 500,
                    'urls': ['http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64']
                }
            ],
            'modules': [],
            'sec_updates': [
                {
                    'name': 'openssl',
                    'version': '3.0.2-0ubuntu1.13',
                    'arch': 'amd64',
                    'repo': 'ubuntu-security'
                }
            ],
            'bug_updates': []
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        report = Report.objects.get(id=response.data['report_id'])
        self.assertEqual(report.host, 'server1.example.com')
        self.assertEqual(report.tags, 'web,production')
        self.assertEqual(report.reboot, 'True')

    def test_upload_missing_required_field(self):
        """Test that missing required fields return 400."""
        data = {
            'protocol': 2,
            'hostname': 'testhost.example.com',
            # missing arch, kernel, os
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'error')
        self.assertIn('errors', response.data)

    def test_upload_wrong_protocol(self):
        """Test that wrong protocol version returns 400."""
        data = {
            'protocol': 1,  # Should be 2
            'hostname': 'testhost.example.com',
            'arch': 'x86_64',
            'kernel': '5.15.0',
            'os': 'Ubuntu 22.04',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_hostname_lowercased(self):
        """Test that hostname is lowercased."""
        data = {
            'protocol': 2,
            'hostname': 'TESTHOST.EXAMPLE.COM',
            'arch': 'x86_64',
            'kernel': '5.15.0',
            'os': 'Ubuntu 22.04',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        report = Report.objects.get(id=response.data['report_id'])
        self.assertEqual(report.host, 'testhost.example.com')

    def test_domain_extracted_from_hostname(self):
        """Test that domain is extracted from FQDN."""
        data = {
            'protocol': 2,
            'hostname': 'server1.prod.example.com',
            'arch': 'x86_64',
            'kernel': '5.15.0',
            'os': 'Ubuntu 22.04',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        report = Report.objects.get(id=response.data['report_id'])
        self.assertEqual(report.domain, 'prod.example.com')

    def test_invalid_package_type(self):
        """Test that invalid package type returns 400."""
        data = {
            'protocol': 2,
            'hostname': 'testhost.example.com',
            'arch': 'x86_64',
            'kernel': '5.15.0',
            'os': 'Ubuntu 22.04',
            'packages': [
                {
                    'name': 'nginx',
                    'version': '1.18.0',
                    'arch': 'amd64',
                    'type': 'invalid'  # Invalid type
                }
            ]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ReportSerializerTests(TestCase):
    """Tests for report serializers."""

    def test_package_serializer_valid(self):
        from reports.serializers import PackageSerializer
        data = {
            'name': 'nginx',
            'epoch': '',
            'version': '1.18.0',
            'release': '6ubuntu14',
            'arch': 'amd64',
            'type': 'deb'
        }
        serializer = PackageSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_package_serializer_minimal(self):
        from reports.serializers import PackageSerializer
        data = {
            'name': 'nginx',
            'version': '1.18.0',
            'arch': 'amd64',
            'type': 'deb'
        }
        serializer = PackageSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_repo_serializer_valid(self):
        from reports.serializers import RepoSerializer
        data = {
            'type': 'deb',
            'name': 'Ubuntu Main',
            'id': 'ubuntu-main',
            'priority': 500,
            'urls': ['http://archive.ubuntu.com/ubuntu']
        }
        serializer = RepoSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_module_serializer_valid(self):
        from reports.serializers import ModuleSerializer
        data = {
            'name': 'nodejs',
            'stream': '18',
            'version': '8090020240101',
            'context': 'rhel9',
            'arch': 'x86_64',
            'repo': 'appstream',
            'packages': ['nodejs-18.19.0-1.module+el9']
        }
        serializer = ModuleSerializer(data=data)
        self.assertTrue(serializer.is_valid())


@override_settings(
    REQUIRE_API_KEY=True,
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ApiKeyAuthTests(APITestCase):
    """Tests for API key authentication using djangorestframework-api-key."""

    def setUp(self):
        self.url = '/api/report/'
        self.api_key_obj, self.api_key = APIKey.objects.create_key(name='test-key')
        self.valid_data = {
            'protocol': 2,
            'hostname': 'testhost.example.com',
            'arch': 'x86_64',
            'kernel': '5.15.0',
            'os': 'Ubuntu 22.04',
        }

    def test_valid_api_key(self):
        """Test that valid API key authenticates."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {self.api_key}')
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_invalid_api_key(self):
        """Test that invalid API key returns 403."""
        self.client.credentials(HTTP_AUTHORIZATION='Api-Key invalid_key')
        response = self.client.post(self.url, self.valid_data, format='json')
        # drf-api-key returns 403 for invalid keys when using HasAPIKey permission
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_revoked_api_key(self):
        """Test that revoked API key returns 403."""
        self.api_key_obj.revoked = True
        self.api_key_obj.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {self.api_key}')
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_missing_api_key_requires_auth(self):
        """Test that missing API key returns 403 when REQUIRE_API_KEY is True."""
        # No credentials set
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(REQUIRE_API_KEY=False)
    def test_no_auth_allowed_when_disabled(self):
        """Test that no auth is allowed when REQUIRE_API_KEY is False."""
        # No credentials set
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
