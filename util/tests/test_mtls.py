"""Tests for mTLS enrollment and certificate management."""

import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from util.models import EnrollmentToken, ClientCertificate


class EnrollmentTokenModelTests(TestCase):
    """Tests for the EnrollmentToken model."""

    def test_create_token(self):
        """Test creating an enrollment token."""
        token = EnrollmentToken.objects.create(
            hostname_pattern='*.example.com',
            expires=timezone.now() + timedelta(hours=24),
        )
        self.assertTrue(token.token.startswith('enroll_'))
        self.assertTrue(token.single_use)
        self.assertEqual(token.used_by, '')

    def test_token_is_valid_before_expiry(self):
        """Test token is valid before expiry."""
        token = EnrollmentToken.objects.create(
            hostname_pattern='*.example.com',
            expires=timezone.now() + timedelta(hours=24),
        )
        self.assertTrue(token.is_valid)

    def test_token_is_invalid_after_expiry(self):
        """Test token is invalid after expiry."""
        token = EnrollmentToken.objects.create(
            hostname_pattern='*.example.com',
            expires=timezone.now() - timedelta(hours=1),
        )
        self.assertFalse(token.is_valid)

    def test_single_use_token_becomes_invalid_after_use(self):
        """Test single-use token becomes invalid after use."""
        token = EnrollmentToken.objects.create(
            hostname_pattern='*.example.com',
            expires=timezone.now() + timedelta(hours=24),
            single_use=True,
        )
        self.assertTrue(token.is_valid)

        token.mark_used('host1.example.com')
        self.assertFalse(token.is_valid)

    def test_multi_use_token_remains_valid_after_use(self):
        """Test multi-use token remains valid after use."""
        token = EnrollmentToken.objects.create(
            hostname_pattern='*.example.com',
            expires=timezone.now() + timedelta(hours=24),
            single_use=False,
        )
        token.mark_used('host1.example.com')
        self.assertTrue(token.is_valid)

    def test_hostname_pattern_matching_wildcard(self):
        """Test wildcard hostname pattern matching."""
        token = EnrollmentToken.objects.create(
            hostname_pattern='*.example.com',
            expires=timezone.now() + timedelta(hours=24),
        )
        self.assertTrue(token.matches_hostname('host1.example.com'))
        self.assertTrue(token.matches_hostname('web.example.com'))
        self.assertFalse(token.matches_hostname('host1.other.com'))

    def test_hostname_pattern_matching_exact(self):
        """Test exact hostname pattern matching."""
        token = EnrollmentToken.objects.create(
            hostname_pattern='specific.example.com',
            expires=timezone.now() + timedelta(hours=24),
        )
        self.assertTrue(token.matches_hostname('specific.example.com'))
        self.assertFalse(token.matches_hostname('other.example.com'))

    def test_hostname_pattern_matching_any(self):
        """Test '*' matches any hostname."""
        token = EnrollmentToken.objects.create(
            hostname_pattern='*',
            expires=timezone.now() + timedelta(hours=24),
        )
        self.assertTrue(token.matches_hostname('anything.example.com'))
        self.assertTrue(token.matches_hostname('any.host.anywhere'))

    def test_token_string_representation(self):
        """Test token __str__ method."""
        token = EnrollmentToken.objects.create(
            hostname_pattern='*.example.com',
            expires=timezone.now() + timedelta(hours=24),
        )
        self.assertIn('active', str(token))


class ClientCertificateModelTests(TestCase):
    """Tests for the ClientCertificate model."""

    def test_create_certificate(self):
        """Test creating a client certificate."""
        cert = ClientCertificate.objects.create(
            hostname='host1.example.com',
            serial_number='ABC123',
            expires_at=timezone.now() + timedelta(days=365),
        )
        self.assertFalse(cert.revoked)
        self.assertIsNone(cert.revoked_at)

    def test_certificate_is_valid(self):
        """Test certificate is valid before expiry and not revoked."""
        cert = ClientCertificate.objects.create(
            hostname='host1.example.com',
            serial_number='ABC123',
            expires_at=timezone.now() + timedelta(days=365),
        )
        self.assertTrue(cert.is_valid)

    def test_certificate_is_invalid_when_expired(self):
        """Test certificate is invalid when expired."""
        cert = ClientCertificate.objects.create(
            hostname='host1.example.com',
            serial_number='ABC123',
            expires_at=timezone.now() - timedelta(days=35),
        )
        self.assertFalse(cert.is_valid)

    def test_certificate_is_invalid_when_revoked(self):
        """Test certificate is invalid when revoked."""
        cert = ClientCertificate.objects.create(
            hostname='host1.example.com',
            serial_number='ABC123',
            expires_at=timezone.now() + timedelta(days=365),
        )
        cert.revoke()
        self.assertFalse(cert.is_valid)

    def test_revoke_sets_revoked_at(self):
        """Test revoke() sets revoked and revoked_at."""
        cert = ClientCertificate.objects.create(
            hostname='host1.example.com',
            serial_number='ABC123',
            expires_at=timezone.now() + timedelta(days=365),
        )
        cert.revoke()
        self.assertTrue(cert.revoked)
        self.assertIsNotNone(cert.revoked_at)

    def test_certificate_string_representation(self):
        """Test certificate __str__ method."""
        cert = ClientCertificate.objects.create(
            hostname='host1.example.com',
            serial_number='ABC123',
            expires_at=timezone.now() + timedelta(days=365),
        )
        self.assertIn('host1.example.com', str(cert))


@override_settings(
    PKI_PROVIDER='util.pki.StepCAProvider',
    PKI_PROVIDER_CONFIG={
        'ca_url': 'https://ca.example.com',
        'provisioner': 'patchman',
        'provisioner_password': 'secret',
    },
)
class EnrollViewTests(APITestCase):
    """Tests for the /api/cert/enroll/ endpoint."""

    def setUp(self):
        """Create test tokens."""
        self.valid_token = EnrollmentToken.objects.create(
            hostname_pattern='*.example.com',
            expires=timezone.now() + timedelta(hours=24),
        )
        self.expired_token = EnrollmentToken.objects.create(
            hostname_pattern='*.example.com',
            expires=timezone.now() - timedelta(hours=1),
        )
        self.sample_csr = """-----BEGIN CERTIFICATE REQUEST-----
MIICYjCCAUoCAQAwHTEbMBkGA1UEAwwSaG9zdDEuZXhhbXBsZS5jb20wggEiMA0G
CSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC7o5e7QFXHJ2YdPJ1qKlWPp8QnHo0j
-----END CERTIFICATE REQUEST-----"""

    @patch('util.views.get_pki_provider')
    def test_enroll_with_valid_token(self, mock_get_provider):
        """Test successful enrollment with valid token."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.sign_csr.return_value = ('-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----', 'SERIAL123')
        mock_get_provider.return_value = mock_provider

        url = reverse('cert-enroll')
        response = self.client.post(url, {
            'token': self.valid_token.token,
            'csr': self.sample_csr,
            'hostname': 'host1.example.com',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('certificate', response.data)

    @patch('util.views.get_pki_provider')
    def test_enroll_with_expired_token(self, mock_get_provider):
        """Test enrollment fails with expired token."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_get_provider.return_value = mock_provider

        url = reverse('cert-enroll')
        response = self.client.post(url, {
            'token': self.expired_token.token,
            'csr': self.sample_csr,
            'hostname': 'host1.example.com',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    @patch('util.views.get_pki_provider')
    def test_enroll_with_invalid_token(self, mock_get_provider):
        """Test enrollment fails with non-existent token."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_get_provider.return_value = mock_provider

        url = reverse('cert-enroll')
        response = self.client.post(url, {
            'token': 'enroll_nonexistent',
            'csr': self.sample_csr,
            'hostname': 'host1.example.com',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('util.views.get_pki_provider')
    def test_enroll_with_hostname_mismatch(self, mock_get_provider):
        """Test enrollment fails when hostname doesn't match pattern."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_get_provider.return_value = mock_provider

        url = reverse('cert-enroll')
        response = self.client.post(url, {
            'token': self.valid_token.token,
            'csr': self.sample_csr,
            'hostname': 'host1.other.com',  # Doesn't match *.example.com
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_enroll_missing_csr(self):
        """Test enrollment fails without CSR."""
        url = reverse('cert-enroll')
        response = self.client.post(url, {
            'token': self.valid_token.token,
            'hostname': 'host1.example.com',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    REQUIRE_CLIENT_CERT=False,
    CLIENT_CERT_CN_HEADER='HTTP_X_SSL_CLIENT_CN',
    CLIENT_CERT_VERIFY_HEADER='HTTP_X_SSL_CLIENT_VERIFY',
    MIDDLEWARE=[
        'django.middleware.common.CommonMiddleware',
        'util.middleware.ClientCertMiddleware',
    ],
)
class RenewViewTests(APITestCase):
    """Tests for the /api/cert/renew/ endpoint."""

    def setUp(self):
        """Create test certificate."""
        self.cert = ClientCertificate.objects.create(
            hostname='host1.example.com',
            serial_number='ABC123',
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.sample_csr = """-----BEGIN CERTIFICATE REQUEST-----
MIICYjCCAUoCAQAwHTEbMBkGA1UEAwwSaG9zdDEuZXhhbXBsZS5jb20wggEiMA0G
-----END CERTIFICATE REQUEST-----"""

    @patch('util.views.get_pki_provider')
    def test_renew_with_valid_cert(self, mock_get_provider):
        """Test successful renewal with valid certificate."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.sign_csr.return_value = ('-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----', 'SERIAL123')
        mock_get_provider.return_value = mock_provider

        url = reverse('cert-renew')
        response = self.client.post(
            url,
            {'csr': self.sample_csr, 'hostname': 'host1.example.com'},
            format='json',
            HTTP_X_SSL_CLIENT_CN='host1.example.com',
            HTTP_X_SSL_CLIENT_VERIFY='SUCCESS',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('certificate', response.data)

    def test_renew_without_cert(self):
        """Test renewal fails without client certificate."""
        url = reverse('cert-renew')
        response = self.client.post(
            url,
            {'csr': self.sample_csr, 'hostname': 'host1.example.com'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_renew_hostname_mismatch(self):
        """Test renewal fails when hostname doesn't match certificate."""
        url = reverse('cert-renew')
        response = self.client.post(
            url,
            {'csr': self.sample_csr, 'hostname': 'other.example.com'},
            format='json',
            HTTP_X_SSL_CLIENT_CN='host1.example.com',  # Different from request
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MiddlewareTests(TestCase):
    """Tests for the ClientCertMiddleware."""

    def test_middleware_extracts_cn(self):
        """Test middleware extracts CN from header."""
        from django.test import RequestFactory
        from util.middleware import ClientCertMiddleware

        factory = RequestFactory()
        request = factory.get('/', HTTP_X_SSL_CLIENT_CN='host1.example.com')

        middleware = ClientCertMiddleware(lambda r: None)
        middleware(request)

        self.assertEqual(request.client_cert_cn, 'host1.example.com')

    def test_middleware_no_header(self):
        """Test middleware handles missing header."""
        from django.test import RequestFactory
        from util.middleware import ClientCertMiddleware

        factory = RequestFactory()
        request = factory.get('/')

        middleware = ClientCertMiddleware(lambda r: None)
        middleware(request)

        self.assertEqual(request.client_cert_cn, '')


class PKIProviderTests(TestCase):
    """Tests for PKI provider classes."""

    def test_get_pki_provider_returns_none_when_not_configured(self):
        """Test get_pki_provider returns None when not configured."""
        from util.pki import get_pki_provider

        with self.settings(PKI_PROVIDER=None):
            provider = get_pki_provider()
            self.assertIsNone(provider)

    @override_settings(
        PKI_PROVIDER='util.pki.StepCAProvider',
        PKI_PROVIDER_CONFIG={'ca_url': 'https://ca.example.com'},
    )
    def test_get_pki_provider_returns_step_ca(self):
        """Test get_pki_provider returns StepCAProvider when configured."""
        from util.pki import get_pki_provider

        provider = get_pki_provider()
        self.assertIsNotNone(provider)
        from util.pki import StepCAProvider
        self.assertIsInstance(provider, StepCAProvider)

    @override_settings(
        PKI_PROVIDER='util.pki.StepCAProvider',
        PKI_PROVIDER_CONFIG={'ca_url': 'https://ca.example.com'},
    )
    def test_step_ca_provider_is_available_without_cli(self):
        """Test StepCAProvider.is_available checks for step CLI."""
        from util.pki import StepCAProvider

        provider = StepCAProvider()
        # Will be False unless step CLI is installed
        result = provider.is_available()
        self.assertIsInstance(result, bool)
