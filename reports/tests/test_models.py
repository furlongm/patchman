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

import json

from django.test import TestCase, override_settings

from reports.models import Report


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ReportModelTests(TestCase):
    """Tests for the Report model."""

    def test_report_creation(self):
        """Test creating a report."""
        report = Report.objects.create(
            host='testhost.example.com',
            domain='example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
        )
        self.assertEqual(report.host, 'testhost.example.com')
        self.assertEqual(report.protocol, '2')
        self.assertFalse(report.processed)

    def test_report_string_representation(self):
        """Test Report __str__ method."""
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
        )
        str_repr = str(report)
        self.assertIn('testhost.example.com', str_repr)

    def test_report_get_absolute_url(self):
        """Test Report.get_absolute_url()."""
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
        )
        url = report.get_absolute_url()
        self.assertIn(str(report.id), url)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ReportParsedPropertiesTests(TestCase):
    """Tests for Report _parsed properties."""

    def test_packages_parsed_protocol2(self):
        """Test packages_parsed returns parsed JSON for protocol 2."""
        packages = [
            {'name': 'nginx', 'version': '1.18.0', 'arch': 'amd64', 'type': 'deb'}
        ]
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
            packages=json.dumps(packages),
        )
        self.assertEqual(report.packages_parsed, packages)
        self.assertEqual(len(report.packages_parsed), 1)
        self.assertEqual(report.packages_parsed[0]['name'], 'nginx')

    def test_packages_parsed_empty(self):
        """Test packages_parsed returns empty list when no packages."""
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
            packages='',
        )
        self.assertEqual(report.packages_parsed, [])

    def test_packages_parsed_invalid_json(self):
        """Test packages_parsed returns empty list for invalid JSON."""
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
            packages='invalid json {',
        )
        self.assertEqual(report.packages_parsed, [])

    def test_packages_parsed_protocol1(self):
        """Test packages_parsed returns empty list for protocol 1."""
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='1',
            packages='nginx 1.18.0 amd64',
        )
        self.assertEqual(report.packages_parsed, [])

    def test_repos_parsed_protocol2(self):
        """Test repos_parsed returns parsed JSON for protocol 2."""
        repos = [
            {'type': 'deb', 'name': 'ubuntu-main', 'id': 'main', 'urls': ['http://example.com']}
        ]
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
            repos=json.dumps(repos),
        )
        self.assertEqual(report.repos_parsed, repos)

    def test_modules_parsed_protocol2(self):
        """Test modules_parsed returns parsed JSON for protocol 2."""
        modules = [
            {'name': 'nodejs', 'stream': '18', 'version': '123', 'context': 'rhel9'}
        ]
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
            modules=json.dumps(modules),
        )
        self.assertEqual(report.modules_parsed, modules)

    def test_sec_updates_parsed_protocol2(self):
        """Test sec_updates_parsed returns parsed JSON for protocol 2."""
        updates = [
            {'name': 'openssl', 'version': '3.0.1', 'arch': 'amd64', 'repo': 'security'}
        ]
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
            sec_updates=json.dumps(updates),
        )
        self.assertEqual(report.sec_updates_parsed, updates)

    def test_bug_updates_parsed_protocol2(self):
        """Test bug_updates_parsed returns parsed JSON for protocol 2."""
        updates = [
            {'name': 'curl', 'version': '7.81.0', 'arch': 'amd64', 'repo': 'main'}
        ]
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
            bug_updates=json.dumps(updates),
        )
        self.assertEqual(report.bug_updates_parsed, updates)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ReportHasPropertiesTests(TestCase):
    """Tests for Report has_* properties."""

    def test_has_packages_protocol2_with_data(self):
        """Test has_packages returns True when packages exist (protocol 2)."""
        packages = [{'name': 'nginx', 'version': '1.18.0', 'arch': 'amd64', 'type': 'deb'}]
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
            packages=json.dumps(packages),
        )
        self.assertTrue(report.has_packages)

    def test_has_packages_protocol2_empty(self):
        """Test has_packages returns False when no packages (protocol 2)."""
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
            packages=json.dumps([]),
        )
        self.assertFalse(report.has_packages)

    def test_has_packages_protocol1_with_data(self):
        """Test has_packages returns True when packages exist (protocol 1)."""
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='1',
            packages='nginx 1.18.0 amd64\ncurl 7.81.0 amd64',
        )
        self.assertTrue(report.has_packages)

    def test_has_packages_protocol1_empty(self):
        """Test has_packages returns False when no packages (protocol 1)."""
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='1',
            packages='',
        )
        self.assertFalse(report.has_packages)

    def test_has_packages_protocol1_whitespace(self):
        """Test has_packages returns False for whitespace-only (protocol 1)."""
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='1',
            packages='   \n\n  ',
        )
        self.assertFalse(report.has_packages)

    def test_has_repos_protocol2(self):
        """Test has_repos property for protocol 2."""
        repos = [{'type': 'deb', 'name': 'main', 'urls': ['http://example.com']}]
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
            repos=json.dumps(repos),
        )
        self.assertTrue(report.has_repos)

    def test_has_modules_protocol2(self):
        """Test has_modules property for protocol 2."""
        modules = [{'name': 'nodejs', 'stream': '18'}]
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
            modules=json.dumps(modules),
        )
        self.assertTrue(report.has_modules)

    def test_has_sec_updates_protocol2(self):
        """Test has_sec_updates property for protocol 2."""
        updates = [{'name': 'openssl', 'version': '3.0.1'}]
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
            sec_updates=json.dumps(updates),
        )
        self.assertTrue(report.has_sec_updates)

    def test_has_bug_updates_protocol2(self):
        """Test has_bug_updates property for protocol 2."""
        updates = [{'name': 'curl', 'version': '7.81.0'}]
        report = Report.objects.create(
            host='testhost.example.com',
            kernel='5.15.0',
            arch='x86_64',
            os='Ubuntu 22.04',
            protocol='2',
            bug_updates=json.dumps(updates),
        )
        self.assertTrue(report.has_bug_updates)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ReportParseMethodTests(TestCase):
    """Tests for Report.parse() method."""

    def test_parse_basic_data(self):
        """Test parse() sets basic report attributes."""
        report = Report()
        data = {
            'host': 'TESTHOST.EXAMPLE.COM',
            'arch': 'x86_64',
            'kernel': '5.15.0',
            'os': 'Ubuntu 22.04',
            'protocol': '2',
        }
        meta = {
            'REMOTE_ADDR': '192.168.1.100',
            'HTTP_USER_AGENT': 'patchman-client/1.0',
        }
        report.parse(data, meta)

        self.assertEqual(report.host, 'testhost.example.com')  # Lowercased
        self.assertEqual(report.domain, 'example.com')  # Extracted
        self.assertEqual(report.arch, 'x86_64')
        self.assertEqual(report.kernel, '5.15.0')
        self.assertEqual(report.os, 'Ubuntu 22.04')
        self.assertEqual(report.protocol, '2')
        self.assertEqual(report.report_ip, '192.168.1.100')
        self.assertEqual(report.useragent, 'patchman-client/1.0')

    def test_parse_extracts_domain_from_fqdn(self):
        """Test parse() extracts domain from FQDN."""
        report = Report()
        data = {
            'host': 'server1.prod.example.com',
            'arch': 'x86_64',
            'kernel': '5.15.0',
            'os': 'Ubuntu 22.04',
            'protocol': '2',
        }
        meta = {
            'REMOTE_ADDR': '192.168.1.100',
            'HTTP_USER_AGENT': 'patchman-client/1.0',
        }
        report.parse(data, meta)

        self.assertEqual(report.host, 'server1.prod.example.com')
        self.assertEqual(report.domain, 'prod.example.com')

    def test_parse_hostname_without_domain(self):
        """Test parse() handles hostname without domain."""
        report = Report()
        data = {
            'host': 'localhost',
            'arch': 'x86_64',
            'kernel': '5.15.0',
            'os': 'Ubuntu 22.04',
            'protocol': '2',
        }
        meta = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': 'patchman-client/1.0',
        }
        report.parse(data, meta)

        self.assertEqual(report.host, 'localhost')
        self.assertIsNone(report.domain)

    def test_parse_x_forwarded_for(self):
        """Test parse() uses X-Forwarded-For header."""
        report = Report()
        data = {
            'host': 'testhost.example.com',
            'arch': 'x86_64',
            'kernel': '5.15.0',
            'os': 'Ubuntu 22.04',
            'protocol': '2',
        }
        meta = {
            'REMOTE_ADDR': '10.0.0.1',
            'HTTP_X_FORWARDED_FOR': '203.0.113.50, 10.0.0.1',
            'HTTP_USER_AGENT': 'patchman-client/1.0',
        }
        report.parse(data, meta)

        self.assertEqual(report.report_ip, '203.0.113.50')

    def test_parse_x_real_ip(self):
        """Test parse() uses X-Real-IP header."""
        report = Report()
        data = {
            'host': 'testhost.example.com',
            'arch': 'x86_64',
            'kernel': '5.15.0',
            'os': 'Ubuntu 22.04',
            'protocol': '2',
        }
        meta = {
            'REMOTE_ADDR': '10.0.0.1',
            'HTTP_X_REAL_IP': '203.0.113.100',
            'HTTP_USER_AGENT': 'patchman-client/1.0',
        }
        report.parse(data, meta)

        self.assertEqual(report.report_ip, '203.0.113.100')

    def test_parse_with_packages(self):
        """Test parse() stores packages data."""
        report = Report()
        packages_data = 'nginx 1.18.0 amd64\ncurl 7.81.0 amd64'
        data = {
            'host': 'testhost.example.com',
            'arch': 'x86_64',
            'kernel': '5.15.0',
            'os': 'Ubuntu 22.04',
            'protocol': '1',
            'packages': packages_data,
        }
        meta = {
            'REMOTE_ADDR': '192.168.1.100',
            'HTTP_USER_AGENT': 'patchman-client/1.0',
        }
        report.parse(data, meta)

        self.assertEqual(report.packages, packages_data)

    def test_parse_with_tags(self):
        """Test parse() stores tags."""
        report = Report()
        data = {
            'host': 'testhost.example.com',
            'arch': 'x86_64',
            'kernel': '5.15.0',
            'os': 'Ubuntu 22.04',
            'protocol': '2',
            'tags': 'web,production',
        }
        meta = {
            'REMOTE_ADDR': '192.168.1.100',
            'HTTP_USER_AGENT': 'patchman-client/1.0',
        }
        report.parse(data, meta)

        self.assertEqual(report.tags, 'web,production')

    def test_parse_with_reboot(self):
        """Test parse() stores reboot status."""
        report = Report()
        data = {
            'host': 'testhost.example.com',
            'arch': 'x86_64',
            'kernel': '5.15.0',
            'os': 'Ubuntu 22.04',
            'protocol': '2',
            'reboot': 'True',
        }
        meta = {
            'REMOTE_ADDR': '192.168.1.100',
            'HTTP_USER_AGENT': 'patchman-client/1.0',
        }
        report.parse(data, meta)

        self.assertEqual(report.reboot, 'True')
