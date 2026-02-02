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

import gzip
import hashlib
from io import BytesIO
from unittest.mock import MagicMock

from django.test import TestCase, override_settings

from util import (
    Checksum, bunzip2, extract, get_checksum, get_md5, get_sha1, get_sha256,
    get_sha512, gunzip, has_setting_of_type, is_epoch_time, response_is_valid,
    sanitize_filter_params, tz_aware_datetime,
)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ChecksumTests(TestCase):
    """Tests for checksum functions."""

    def test_get_sha256(self):
        """Test SHA256 hash generation."""
        data = b'test data for hashing'
        expected = hashlib.sha256(data).hexdigest()
        result = get_sha256(data)
        self.assertEqual(result, expected)

    def test_get_sha1(self):
        """Test SHA1 hash generation."""
        data = b'test data for hashing'
        expected = hashlib.sha1(data).hexdigest()
        result = get_sha1(data)
        self.assertEqual(result, expected)

    def test_get_sha512(self):
        """Test SHA512 hash generation."""
        data = b'test data for hashing'
        expected = hashlib.sha512(data).hexdigest()
        result = get_sha512(data)
        self.assertEqual(result, expected)

    def test_get_md5(self):
        """Test MD5 hash generation."""
        data = b'test data for hashing'
        expected = hashlib.md5(data).hexdigest()
        result = get_md5(data)
        self.assertEqual(result, expected)

    def test_get_checksum_sha256(self):
        """Test get_checksum with sha256."""
        data = b'test data'
        expected = hashlib.sha256(data).hexdigest()
        result = get_checksum(data, Checksum.sha256)
        self.assertEqual(result, expected)

    def test_get_checksum_sha1(self):
        """Test get_checksum with sha1."""
        data = b'test data'
        expected = hashlib.sha1(data).hexdigest()
        result = get_checksum(data, Checksum.sha1)
        self.assertEqual(result, expected)

    def test_get_checksum_md5(self):
        """Test get_checksum with md5."""
        data = b'test data'
        expected = hashlib.md5(data).hexdigest()
        result = get_checksum(data, Checksum.md5)
        self.assertEqual(result, expected)

    def test_get_checksum_sha512(self):
        """Test get_checksum with sha512."""
        data = b'test data'
        expected = hashlib.sha512(data).hexdigest()
        result = get_checksum(data, Checksum.sha512)
        self.assertEqual(result, expected)

    def test_get_checksum_empty_data(self):
        """Test checksum of empty data."""
        data = b''
        result = get_sha256(data)
        expected = hashlib.sha256(b'').hexdigest()
        self.assertEqual(result, expected)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class CompressionTests(TestCase):
    """Tests for compression/decompression functions."""

    def test_gunzip_valid_data(self):
        """Test gunzip with valid gzipped data."""
        original = b'Hello, World! This is test data.'
        buf = BytesIO()
        with gzip.GzipFile(fileobj=buf, mode='wb') as f:
            f.write(original)
        compressed = buf.getvalue()

        result = gunzip(compressed)
        self.assertEqual(result, original)

    def test_gunzip_invalid_data(self):
        """Test gunzip with invalid data returns None."""
        result = gunzip(b'not gzipped data')
        self.assertIsNone(result)

    def test_bunzip2_invalid_data(self):
        """Test bunzip2 with invalid data returns None."""
        result = bunzip2(b'not bzip2 data')
        self.assertIsNone(result)

    def test_extract_gzip(self):
        """Test extract with gzip format."""
        original = b'test content'
        buf = BytesIO()
        with gzip.GzipFile(fileobj=buf, mode='wb') as f:
            f.write(original)
        compressed = buf.getvalue()

        result = extract(compressed, 'gz')
        self.assertEqual(result, original)

    def test_extract_unknown_format(self):
        """Test extract with unknown format returns original."""
        data = b'unchanged data'
        result = extract(data, 'unknown')
        self.assertEqual(result, data)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class URLFetchTests(TestCase):
    """Tests for URL fetching functions."""

    def test_response_is_valid_200(self):
        """Test response_is_valid with 200 status."""
        mock_response = MagicMock()
        mock_response.ok = True
        self.assertTrue(response_is_valid(mock_response))

    def test_response_is_valid_error(self):
        """Test response_is_valid with error status."""
        mock_response = MagicMock()
        mock_response.ok = False
        self.assertFalse(response_is_valid(mock_response))

    def test_response_is_valid_none(self):
        """Test response_is_valid with None."""
        self.assertFalse(response_is_valid(None))


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class SanitizeFilterParamsTests(TestCase):
    """Tests for sanitize_filter_params function."""

    def test_sanitize_simple_params(self):
        """Test sanitizing simple filter params."""
        params = 'name=test&version=1.0'
        result = sanitize_filter_params(params)
        self.assertIn('name=test', result)
        self.assertIn('version=1.0', result)

    def test_sanitize_empty_params(self):
        """Test sanitizing empty params."""
        result = sanitize_filter_params('')
        self.assertEqual(result, '')

    def test_sanitize_none_params(self):
        """Test sanitizing None params."""
        result = sanitize_filter_params(None)
        self.assertEqual(result, '')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class DateTimeTests(TestCase):
    """Tests for datetime utility functions."""

    def test_is_epoch_time_valid(self):
        """Test is_epoch_time with valid epoch timestamp."""
        self.assertTrue(is_epoch_time(1704067200))  # 2024-01-01 00:00:00

    def test_is_epoch_time_invalid_string(self):
        """Test is_epoch_time with non-numeric string."""
        self.assertFalse(is_epoch_time('not-a-number'))

    def test_is_epoch_time_too_large(self):
        """Test is_epoch_time with unreasonably large value."""
        self.assertFalse(is_epoch_time(99999999999999))

    def test_is_epoch_time_negative(self):
        """Test is_epoch_time with negative value."""
        self.assertFalse(is_epoch_time(-1))

    def test_tz_aware_datetime_from_epoch(self):
        """Test converting epoch timestamp to timezone-aware datetime."""
        epoch = 1704067200  # 2024-01-01 00:00:00 UTC
        result = tz_aware_datetime(epoch)
        self.assertIsNotNone(result.tzinfo)

    def test_tz_aware_datetime_from_string(self):
        """Test converting string datetime to timezone-aware."""
        date_str = '2024-01-01T12:00:00'
        result = tz_aware_datetime(date_str)
        self.assertIsNotNone(result.tzinfo)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class SettingsTests(TestCase):
    """Tests for settings utility functions."""

    @override_settings(TEST_STRING_SETTING='test_value')
    def test_has_setting_of_type_string_exists(self):
        """Test has_setting_of_type with existing string setting."""
        result = has_setting_of_type('TEST_STRING_SETTING', str)
        self.assertTrue(result)

    def test_has_setting_of_type_missing(self):
        """Test has_setting_of_type with missing setting."""
        result = has_setting_of_type('NONEXISTENT_SETTING_XYZ', str)
        self.assertFalse(result)

    @override_settings(TEST_INT_SETTING=42)
    def test_has_setting_of_type_wrong_type(self):
        """Test has_setting_of_type with wrong type."""
        result = has_setting_of_type('TEST_INT_SETTING', str)
        self.assertFalse(result)

    @override_settings(TEST_BOOL_SETTING=True)
    def test_has_setting_of_type_bool(self):
        """Test has_setting_of_type with bool setting."""
        result = has_setting_of_type('TEST_BOOL_SETTING', bool)
        self.assertTrue(result)
