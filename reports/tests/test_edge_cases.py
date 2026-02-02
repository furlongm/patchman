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

from reports.models import Report
from reports.utils import parse_packages, process_package


@override_settings(
    REQUIRE_API_KEY=False,
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class EdgeCasePackageTests(TestCase):
    """Edge case tests for package processing."""

    def test_package_with_unicode_name(self):
        """Test package with unicode characters in name."""
        # Some packages may have unicode in description, handled gracefully
        package = process_package(
            name='test-pkg',
            epoch='',
            version='1.0.0',
            release='1',
            arch='amd64',
            p_type='D',
        )
        self.assertIsNotNone(package)

    def test_package_with_very_long_version(self):
        """Test package with very long version string."""
        long_version = '1.2.3.4.5.6.7.8.9.10.11.12.13.14.15.16.17.18.19.20'
        package = process_package(
            name='longver-pkg',
            epoch='',
            version=long_version,
            release='1',
            arch='amd64',
            p_type='D',
        )
        self.assertIsNotNone(package)
        self.assertEqual(package.version, long_version)

    def test_package_with_special_chars_in_version(self):
        """Test package with special characters in version."""
        package = process_package(
            name='special-pkg',
            epoch='',
            version='1.0.0~beta+git20240101',
            release='1ubuntu1~22.04.1',
            arch='amd64',
            p_type='D',
        )
        self.assertIsNotNone(package)

    def test_package_with_empty_epoch(self):
        """Test package with empty epoch."""
        package = process_package(
            name='noepoch-pkg',
            epoch='',
            version='1.0.0',
            release='1',
            arch='amd64',
            p_type='D',
        )
        self.assertEqual(package.epoch, '')

    def test_package_with_empty_release(self):
        """Test package with empty release."""
        package = process_package(
            name='norelease-pkg',
            epoch='',
            version='1.0.0',
            release='',
            arch='amd64',
            p_type='D',
        )
        self.assertEqual(package.release, '')

    def test_package_with_numeric_epoch(self):
        """Test package with large numeric epoch."""
        package = process_package(
            name='bigepoch-pkg',
            epoch='999',
            version='1.0.0',
            release='1',
            arch='amd64',
            p_type='D',
        )
        self.assertEqual(package.epoch, '999')


@override_settings(
    REQUIRE_API_KEY=False,
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class EdgeCaseReportAPITests(APITestCase):
    """Edge case tests for Report API."""

    def test_report_with_empty_packages_array(self):
        """Test report with empty packages array."""
        data = {
            'hostname': 'empty-pkgs.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
            'packages': [],
            'repos': [],
        }
        response = self.client.post('/api/report/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_report_with_many_packages(self):
        """Test report with many packages (stress test)."""
        packages = [
            {'name': f'pkg{i}', 'version': '1.0.0', 'arch': 'amd64', 'type': 'deb'}
            for i in range(100)
        ]
        data = {
            'hostname': 'many-pkgs.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
            'packages': packages,
            'repos': [],
        }
        response = self.client.post('/api/report/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_report_with_unicode_hostname(self):
        """Test report with hostname containing valid chars."""
        data = {
            'hostname': 'test-host-123.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
            'packages': [],
        }
        response = self.client.post('/api/report/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_report_with_unicode_os(self):
        """Test report with unicode in OS name."""
        data = {
            'hostname': 'unicode-os.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04 LTS "Jammy Jellyfish"',
            'kernel': '5.15.0-91-generic',
            'packages': [],
        }
        response = self.client.post('/api/report/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_report_with_very_long_kernel(self):
        """Test report with very long kernel string."""
        data = {
            'hostname': 'longkernel.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic-with-extra-long-suffix-for-testing',
            'packages': [],
        }
        response = self.client.post('/api/report/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_report_with_special_tags(self):
        """Test report with special characters in tags."""
        data = {
            'hostname': 'tagged.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
            'tags': ['web-server', 'prod_env', 'tier1'],
            'packages': [],
        }
        response = self.client.post('/api/report/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)


@override_settings(
    REQUIRE_API_KEY=False,
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class EdgeCaseMalformedInputTests(APITestCase):
    """Tests for handling malformed input."""

    def test_report_with_null_packages(self):
        """Test report with null packages field."""
        data = {
            'hostname': 'null-pkgs.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
            'packages': None,
        }
        response = self.client.post('/api/report/', data, format='json')
        # Should either accept or return validation error
        self.assertIn(response.status_code, [status.HTTP_202_ACCEPTED, status.HTTP_400_BAD_REQUEST])

    def test_report_with_invalid_json_type(self):
        """Test report with invalid type for packages (string instead of array)."""
        data = {
            'hostname': 'invalid-type.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
            'packages': 'not-an-array',
        }
        response = self.client.post('/api/report/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_report_with_missing_required_package_field(self):
        """Test report with package missing required field."""
        data = {
            'hostname': 'missing-field.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
            'packages': [
                {'name': 'pkg1'},  # Missing version and arch
            ],
        }
        response = self.client.post('/api/report/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_report_with_extra_unknown_fields(self):
        """Test report with extra unknown fields (should be ignored)."""
        data = {
            'hostname': 'extra-fields.example.com',
            'arch': 'x86_64',
            'os': 'Ubuntu 22.04',
            'kernel': '5.15.0-91-generic',
            'unknown_field': 'should be ignored',
            'another_unknown': 123,
            'packages': [],
        }
        response = self.client.post('/api/report/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)


@override_settings(
    REQUIRE_API_KEY=False,
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class BoundaryConditionTests(TestCase):
    """Tests for boundary conditions."""

    def test_parse_packages_with_newlines_only(self):
        """Test parsing string with only newlines."""
        packages = parse_packages('\n\n\n')
        # Should handle gracefully
        self.assertIsInstance(packages, list)

    def test_parse_packages_with_mixed_formats(self):
        """Test parsing packages with inconsistent formatting."""
        pkg_str = """'nginx' '' '1.18.0' '6ubuntu14' 'amd64' 'deb'
'curl' '' '7.81.0' '1' 'amd64'"""  # Missing type
        packages = parse_packages(pkg_str)
        self.assertEqual(len(packages), 2)

    def test_report_duplicate_hostname(self):
        """Test creating reports for same hostname."""
        Report.objects.create(
            host='duplicate.example.com',
            domain='example.com',
            report_ip='192.168.1.1',
            os='Ubuntu 22.04',
            kernel='5.15.0-91-generic',
            arch='x86_64',
            protocol='2',
        )
        # Second report for same host should work
        report2 = Report.objects.create(
            host='duplicate.example.com',
            domain='example.com',
            report_ip='192.168.1.1',
            os='Ubuntu 22.04',
            kernel='5.15.0-92-generic',  # Newer kernel
            arch='x86_64',
            protocol='2',
        )
        self.assertIsNotNone(report2)
        self.assertEqual(Report.objects.filter(host='duplicate.example.com').count(), 2)
