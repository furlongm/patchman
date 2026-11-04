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

from decimal import Decimal
from unittest.mock import patch

import requests
from django.db import IntegrityError
from django.test import TestCase, override_settings

from security.models import CVE, CVSS, CWE, Reference


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class CVEMethodTests(TestCase):
    """Tests for CVE model methods."""

    def test_cve_creation(self):
        """Test creating a CVE."""
        cve = CVE.objects.create(cve_id='CVE-2024-12345')
        self.assertEqual(cve.cve_id, 'CVE-2024-12345')

    def test_cve_str(self):
        """Test CVE __str__ method."""
        cve = CVE.objects.create(cve_id='CVE-2024-12345')
        self.assertEqual(str(cve), 'CVE-2024-12345')

    def test_cve_get_absolute_url(self):
        """Test CVE.get_absolute_url()."""
        cve = CVE.objects.create(cve_id='CVE-2024-12345')
        url = cve.get_absolute_url()
        self.assertIn(str(cve.id), url)

    def test_cve_unique_id(self):
        """Test CVE cve_id is unique."""
        CVE.objects.create(cve_id='CVE-2024-12345')
        with self.assertRaises(IntegrityError):
            CVE.objects.create(cve_id='CVE-2024-12345')

    def test_cve_with_cvss_score(self):
        """Test CVE with associated CVSS scores."""
        cve = CVE.objects.create(cve_id='CVE-2024-99999')
        score = CVSS.objects.create(
            version=Decimal('3.1'),
            vector_string='CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
            score=Decimal('9.8'),
            severity='CRITICAL',
        )
        cve.cvss_scores.add(score)
        self.assertIn(score, cve.cvss_scores.all())

    def _response(self, status_code, content=b''):
        response = requests.Response()
        response.status_code = status_code
        response._content = content
        return response

    def test_fetch_cve_data_skips_error_responses(self):
        """Error or missing responses should be skipped, not crash."""
        cve = CVE.objects.create(cve_id='CVE-2024-1234')
        for response in (self._response(404), self._response(403), None):
            with patch('security.models.get_url', return_value=response), \
                    patch.object(CVE, 'parse_nist_cve_data') as parse_nist, \
                    patch.object(CVE, 'parse_mitre_cve_data') as parse_mitre, \
                    patch.object(CVE, 'parse_osv_dev_cve_data') as parse_osv:
                cve.fetch_cve_data(fetch_nist_data=True, sleep_secs=0)
            parse_nist.assert_not_called()
            parse_mitre.assert_not_called()
            parse_osv.assert_not_called()

    def test_fetch_nist_cve_data_parses_valid_response(self):
        """A valid NIST response should be parsed."""
        cve = CVE.objects.create(cve_id='CVE-2024-1234')
        response = self._response(200, b'{"vulnerabilities": []}')
        with patch('security.models.get_url', return_value=response), \
                patch.object(CVE, 'parse_nist_cve_data') as parse_nist:
            cve.fetch_nist_cve_data()
        parse_nist.assert_called_once_with({'vulnerabilities': []})


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class CWEMethodTests(TestCase):
    """Tests for CWE model methods."""

    def test_cwe_creation(self):
        """Test creating a CWE."""
        cwe = CWE.objects.create(cwe_id='CWE-79', name='Cross-site Scripting')
        self.assertEqual(cwe.cwe_id, 'CWE-79')

    def test_cwe_str(self):
        """Test CWE __str__ method."""
        cwe = CWE.objects.create(cwe_id='CWE-79', name='Cross-site Scripting')
        self.assertEqual(str(cwe), 'CWE-79 - Cross-site Scripting')

    def test_cwe_get_absolute_url(self):
        """Test CWE.get_absolute_url()."""
        cwe = CWE.objects.create(cwe_id='CWE-79', name='XSS')
        url = cwe.get_absolute_url()
        self.assertIn('CWE-79', url)

    def test_cwe_unique_id(self):
        """Test CWE cwe_id is unique."""
        CWE.objects.create(cwe_id='CWE-79', name='XSS')
        with self.assertRaises(IntegrityError):
            CWE.objects.create(cwe_id='CWE-79', name='Different name')

    def test_cwe_int_id_property(self):
        """Test CWE.int_id property extracts numeric part."""
        cwe = CWE.objects.create(cwe_id='CWE-79', name='XSS')
        self.assertEqual(cwe.int_id, 79)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class CVSSMethodTests(TestCase):
    """Tests for CVSS model methods."""

    def test_cvss_creation(self):
        """Test creating a CVSS."""
        score = CVSS.objects.create(
            version=Decimal('3.1'),
            vector_string='CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
            score=Decimal('9.8'),
            severity='CRITICAL',
        )
        self.assertEqual(score.version, Decimal('3.1'))
        self.assertEqual(score.score, Decimal('9.8'))

    def test_cvss_str(self):
        """Test CVSS __str__ method."""
        score = CVSS.objects.create(
            version=Decimal('3.1'),
            vector_string='CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
            score=Decimal('9.8'),
            severity='CRITICAL',
        )
        str_repr = str(score)
        self.assertIn('9.8', str_repr)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ReferenceMethodTests(TestCase):
    """Tests for Reference model methods."""

    def test_reference_creation(self):
        """Test creating a Reference."""
        ref = Reference.objects.create(
            url='https://nvd.nist.gov/vuln/detail/CVE-2024-12345',
            ref_type='NVD',
        )
        self.assertEqual(ref.ref_type, 'NVD')

    def test_reference_str(self):
        """Test Reference __str__ method."""
        ref = Reference.objects.create(
            url='https://example.com/advisory',
            ref_type='VENDOR',
        )
        str_repr = str(ref)
        self.assertIn('example.com', str_repr)

    def test_reference_unique_together(self):
        """Test Reference unique constraint."""
        Reference.objects.create(
            url='https://example.com/advisory',
            ref_type='VENDOR',
        )
        with self.assertRaises(IntegrityError):
            Reference.objects.create(
                url='https://example.com/advisory',
                ref_type='VENDOR',
            )

    def test_reference_same_url_different_type(self):
        """Test same URL with different ref_type is allowed."""
        Reference.objects.create(
            url='https://example.com/advisory',
            ref_type='VENDOR',
        )
        ref2 = Reference.objects.create(
            url='https://example.com/advisory',
            ref_type='ADVISORY',
        )
        self.assertEqual(ref2.ref_type, 'ADVISORY')
