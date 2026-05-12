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

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.dateparse import parse_datetime

from django.utils import timezone

from patchman.arch.models import MachineArchitecture
from patchman.compliance.models import (
    ComplianceProfile, ComplianceResult, ComplianceRule, ComplianceScan,
)
from patchman.compliance.utils import process_compliance_json
from patchman.domains.models import Domain
from patchman.hosts.models import Host
from patchman.operatingsystems.models import OSRelease, OSVariant
from patchman.reports.models import Report

SAMPLE_COMPLIANCE = {
    'version': '1.0.0',
    'scan_date': '2026-01-01T00:00:00+00:00',
    'hostname': 'testhost',
    'os_id': 'rhel',
    'os_version': '9.3',
    'datastream': 'ssg-rhel9-ds.xml',
    'profile': 'xccdf_org.ssgproject.content_profile_cis',
    'target': 'testhost.example.com',
    'score': 85.5,
    'score_maximum': 100.0,
    'start_time': '2026-01-01T00:00:00',
    'end_time': '2026-01-01T00:05:00',
    'summary': {
        'pass': 120, 'fail': 15, 'error': 0,
        'notapplicable': 30, 'notchecked': 5,
        'notselected': 0, 'informational': 0, 'fixed': 0,
    },
    'rules': [
        {'id': 'xccdf_org.ssgproject.content_rule_1', 'severity': 'high', 'result': 'pass'},
        {'id': 'xccdf_org.ssgproject.content_rule_2', 'severity': 'medium', 'result': 'fail'},
        {'id': 'xccdf_org.ssgproject.content_rule_3', 'severity': 'low', 'result': 'notapplicable'},
    ],
}


def _create_host(hostname='testhost', ipaddress='192.168.1.1'):
    """Helper to create a host with required related objects."""
    osrelease, _ = OSRelease.objects.get_or_create(
        name='TestOS 9', defaults={'codename': 'test'},
    )
    osvariant, _ = OSVariant.objects.get_or_create(
        name='TestOS 9.3',
        defaults={'osrelease': osrelease},
    )
    m_arch, _ = MachineArchitecture.objects.get_or_create(name='x86_64')
    domain, _ = Domain.objects.get_or_create(name='example.com')
    host, _ = Host.objects.get_or_create(
        hostname=hostname,
        defaults={
            'ipaddress': ipaddress,
            'arch': m_arch,
            'osvariant': osvariant,
            'domain': domain,
            'lastreport': timezone.now(),
        },
    )
    return host


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class ComplianceProfileTests(TestCase):
    """Tests for ComplianceProfile model."""

    def test_profile_creation(self):
        profile = ComplianceProfile.objects.create(
            profile_id='xccdf_org.ssgproject.content_profile_cis',
        )
        self.assertEqual(profile.profile_id, 'xccdf_org.ssgproject.content_profile_cis')

    def test_profile_str(self):
        profile = ComplianceProfile.objects.create(
            profile_id='xccdf_org.ssgproject.content_profile_cis',
        )
        self.assertEqual(str(profile), 'xccdf_org.ssgproject.content_profile_cis')

    def test_profile_unique_id(self):
        ComplianceProfile.objects.create(
            profile_id='xccdf_org.ssgproject.content_profile_cis',
        )
        with self.assertRaises(IntegrityError):
            ComplianceProfile.objects.create(
                profile_id='xccdf_org.ssgproject.content_profile_cis',
            )


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class ComplianceRuleTests(TestCase):
    """Tests for ComplianceRule model."""

    def test_rule_creation(self):
        rule = ComplianceRule.objects.create(
            rule_id='xccdf_org.ssgproject.content_rule_1',
            severity='high',
        )
        self.assertEqual(rule.rule_id, 'xccdf_org.ssgproject.content_rule_1')
        self.assertEqual(rule.severity, 'high')

    def test_rule_str(self):
        rule = ComplianceRule.objects.create(
            rule_id='xccdf_org.ssgproject.content_rule_1',
        )
        self.assertEqual(str(rule), 'xccdf_org.ssgproject.content_rule_1')

    def test_rule_unique_id(self):
        ComplianceRule.objects.create(
            rule_id='xccdf_org.ssgproject.content_rule_1',
        )
        with self.assertRaises(IntegrityError):
            ComplianceRule.objects.create(
                rule_id='xccdf_org.ssgproject.content_rule_1',
            )


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class ComplianceScanTests(TestCase):
    """Tests for ComplianceScan model."""

    def setUp(self):
        self.host = _create_host()
        self.profile = ComplianceProfile.objects.create(
            profile_id='test_profile',
        )

    def test_scan_creation(self):
        scan = ComplianceScan.objects.create(
            host=self.host,
            profile=self.profile,
            score=85.5,
            scanned_at='2026-01-01T00:00:00Z',
        )
        self.assertEqual(scan.score, 85.5)

    def test_scan_unique_constraint(self):
        ComplianceScan.objects.create(
            host=self.host,
            profile=self.profile,
            scanned_at='2026-01-01T00:00:00Z',
        )
        with self.assertRaises(IntegrityError):
            ComplianceScan.objects.create(
                host=self.host,
                profile=self.profile,
                scanned_at='2026-01-01T00:00:00Z',
            )


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class ComplianceResultTests(TestCase):
    """Tests for ComplianceResult model."""

    def setUp(self):
        self.host = _create_host()
        self.profile = ComplianceProfile.objects.create(
            profile_id='test_profile',
        )
        self.scan = ComplianceScan.objects.create(
            host=self.host,
            profile=self.profile,
            scanned_at='2026-01-01T00:00:00Z',
        )
        self.rule = ComplianceRule.objects.create(
            rule_id='test_rule_1',
            severity='high',
        )

    def test_result_creation(self):
        result = ComplianceResult.objects.create(
            scan=self.scan,
            rule=self.rule,
            result='pass',
        )
        self.assertEqual(result.result, 'pass')

    def test_result_unique_constraint(self):
        ComplianceResult.objects.create(
            scan=self.scan,
            rule=self.rule,
            result='pass',
        )
        with self.assertRaises(IntegrityError):
            ComplianceResult.objects.create(
                scan=self.scan,
                rule=self.rule,
                result='fail',
            )

    def test_result_str(self):
        result = ComplianceResult.objects.create(
            scan=self.scan,
            rule=self.rule,
            result='fail',
        )
        self.assertIn('fail', str(result))


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class ProcessComplianceJsonTests(TestCase):
    """Tests for process_compliance_json utility."""

    def setUp(self):
        self.host = _create_host()

    def test_valid_compliance_json(self):
        """Valid compliance JSON creates scan + results."""
        process_compliance_json(SAMPLE_COMPLIANCE, self.host)

        self.assertEqual(ComplianceProfile.objects.count(), 1)
        self.assertEqual(ComplianceScan.objects.count(), 1)
        self.assertEqual(ComplianceRule.objects.count(), 3)
        self.assertEqual(ComplianceResult.objects.count(), 3)

        scan = ComplianceScan.objects.first()
        self.assertEqual(scan.score, 85.5)
        self.assertEqual(scan.pass_count, 120)
        self.assertEqual(scan.fail_count, 15)
        self.assertEqual(scan.datastream, 'ssg-rhel9-ds.xml')

    def test_duplicate_scan_skipped(self):
        """Duplicate scan (same host+profile+timestamp) is skipped."""
        process_compliance_json(SAMPLE_COMPLIANCE, self.host)
        process_compliance_json(SAMPLE_COMPLIANCE, self.host)

        self.assertEqual(ComplianceScan.objects.count(), 1)
        self.assertEqual(ComplianceResult.objects.count(), 3)

    def test_missing_start_time_uses_scan_date(self):
        """Falls back to scan_date if start_time is missing."""
        data = SAMPLE_COMPLIANCE.copy()
        data.pop('start_time', None)
        process_compliance_json(data, self.host)

        self.assertEqual(ComplianceScan.objects.count(), 1)

    def test_missing_timestamp_skips(self):
        """Scan with no timestamp is skipped."""
        data = SAMPLE_COMPLIANCE.copy()
        data.pop('start_time', None)
        data.pop('scan_date', None)
        process_compliance_json(data, self.host)

        self.assertEqual(ComplianceScan.objects.count(), 0)

    def test_missing_summary(self):
        """Handles missing summary gracefully."""
        data = SAMPLE_COMPLIANCE.copy()
        data.pop('summary', None)
        process_compliance_json(data, self.host)

        scan = ComplianceScan.objects.first()
        self.assertEqual(scan.pass_count, 0)
        self.assertEqual(scan.fail_count, 0)

    def test_empty_rules(self):
        """Handles empty rules list."""
        data = SAMPLE_COMPLIANCE.copy()
        data['rules'] = []
        process_compliance_json(data, self.host)

        self.assertEqual(ComplianceScan.objects.count(), 1)
        self.assertEqual(ComplianceResult.objects.count(), 0)

    def test_existing_rules_reused(self):
        """Existing rules are reused, not duplicated."""
        ComplianceRule.objects.create(
            rule_id='xccdf_org.ssgproject.content_rule_1',
            severity='high',
        )
        process_compliance_json(SAMPLE_COMPLIANCE, self.host)

        self.assertEqual(ComplianceRule.objects.count(), 3)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class ComplianceViewTests(TestCase):
    """Tests for compliance views."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass',
        )
        self.client.login(username='testuser', password='testpass')
        self.host = _create_host()
        self.profile = ComplianceProfile.objects.create(
            profile_id='test_profile',
        )
        self.scan = ComplianceScan.objects.create(
            host=self.host,
            profile=self.profile,
            score=85.5,
            pass_count=120,
            fail_count=15,
            scanned_at='2026-01-01T00:00:00Z',
        )
        self.rule = ComplianceRule.objects.create(
            rule_id='test_rule_1',
            severity='high',
        )
        ComplianceResult.objects.create(
            scan=self.scan,
            rule=self.rule,
            result='pass',
        )

    def test_compliance_summary_200(self):
        response = self.client.get(reverse('compliance:compliance_summary'))
        self.assertEqual(response.status_code, 200)

    def test_compliance_host_200(self):
        response = self.client.get(
            reverse('compliance:compliance_host', args=[self.host.id]),
        )
        self.assertEqual(response.status_code, 200)

    def test_compliance_rule_200(self):
        response = self.client.get(
            reverse('compliance:compliance_rule', args=[self.rule.id]),
        )
        self.assertEqual(response.status_code, 200)

    def test_compliance_host_no_scans(self):
        """Host with no scans returns 200."""
        host2 = _create_host(hostname='host2', ipaddress='192.168.1.2')
        response = self.client.get(
            reverse('compliance:compliance_host', args=[host2.id]),
        )
        self.assertEqual(response.status_code, 200)

    def test_compliance_summary_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('compliance:compliance_summary'))
        self.assertEqual(response.status_code, 302)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class ComplianceStatsAPITests(TestCase):
    """Tests for ComplianceStatsView API."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass',
        )
        self.client.login(username='testuser', password='testpass')
        self.host = _create_host()
        self.profile = ComplianceProfile.objects.create(
            profile_id='test_profile',
        )
        self.scan = ComplianceScan.objects.create(
            host=self.host,
            profile=self.profile,
            score=85.5,
            pass_count=120,
            fail_count=15,
            scanned_at='2026-01-01T00:00:00Z',
        )

    def test_stats_returns_correct_structure(self):
        response = self.client.get(reverse('api-compliance-stats'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total_hosts_scanned', data)
        self.assertIn('average_score', data)
        self.assertIn('compliance_by_result', data)
        self.assertIn('top_failing_rules', data)
        self.assertIn('score_distribution', data)

    def test_stats_values(self):
        response = self.client.get(reverse('api-compliance-stats'))
        data = response.json()
        self.assertEqual(data['total_hosts_scanned'], 1)
        self.assertEqual(data['average_score'], 85.5)
        self.assertEqual(data['score_distribution']['medium'], 1)
        self.assertEqual(data['score_distribution']['high'], 0)
        self.assertEqual(data['score_distribution']['low'], 0)

    def test_stats_requires_auth(self):
        self.client.logout()
        response = self.client.get(reverse('api-compliance-stats'))
        self.assertIn(response.status_code, [401, 403])

    def test_stats_empty_database(self):
        ComplianceScan.objects.all().delete()
        response = self.client.get(reverse('api-compliance-stats'))
        data = response.json()
        self.assertEqual(data['total_hosts_scanned'], 0)
        self.assertEqual(data['average_score'], 0)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class ReportComplianceIntegrationTests(TestCase):
    """Tests for compliance integration in the Report model."""

    def test_report_without_compliance_processes_normally(self):
        """Report without compliance field processes without error."""
        report = Report.objects.create(
            host='testhost',
            os='TestOS 9.3',
            kernel='5.14.0-362.el9.x86_64',
            arch='x86_64',
            protocol='2',
            packages='[]',
            repos='[]',
        )
        self.assertFalse(report.has_compliance)
        self.assertEqual(report.compliance_parsed, {})

    def test_report_compliance_parsed(self):
        """Report with compliance data parses correctly."""
        report = Report.objects.create(
            host='testhost',
            os='TestOS 9.3',
            kernel='5.14.0-362.el9.x86_64',
            arch='x86_64',
            protocol='2',
            packages='[]',
            compliance=json.dumps(SAMPLE_COMPLIANCE),
        )
        self.assertTrue(report.has_compliance)
        parsed = report.compliance_parsed
        self.assertEqual(parsed['profile'], 'xccdf_org.ssgproject.content_profile_cis')

    def test_report_compliance_invalid_json(self):
        """Report with invalid compliance JSON returns empty dict."""
        report = Report.objects.create(
            host='testhost',
            os='TestOS 9.3',
            kernel='5.14.0-362.el9.x86_64',
            arch='x86_64',
            protocol='2',
            packages='[]',
            compliance='not-json',
        )
        self.assertEqual(report.compliance_parsed, {})

    def test_report_protocol1_no_compliance(self):
        """Protocol 1 report has no compliance parsing."""
        report = Report.objects.create(
            host='testhost',
            os='TestOS 9.3',
            kernel='5.14.0-362.el9.x86_64',
            arch='x86_64',
            protocol='1',
        )
        self.assertFalse(report.has_compliance)
