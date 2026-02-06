# Copyright 2024 Marcus Furlong <furlongm@gmail.com>
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

"""
PKI provider abstraction for certificate signing.

Supports multiple CA backends (step-ca, Vault) with a common interface.
"""

import logging
import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class PKIError(Exception):
    """Base exception for PKI operations."""
    pass


class PKIProvider(ABC):
    """Base class for PKI providers."""

    @abstractmethod
    def sign_csr(self, csr_pem: str, hostname: str, validity_days: int) -> tuple[str, str]:
        """
        Sign a CSR and return the certificate.

        Args:
            csr_pem: PEM-encoded Certificate Signing Request
            hostname: Expected CN/SAN hostname
            validity_days: Certificate validity period

        Returns:
            Tuple of (certificate_pem, serial_number)

        Raises:
            PKIError: If signing fails
        """
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is properly configured and available."""
        raise NotImplementedError


class StepCAProvider(PKIProvider):
    """PKI provider using step-ca (Smallstep)."""

    def __init__(self):
        config = getattr(settings, 'PKI_PROVIDER_CONFIG', {})
        self.ca_url = config.get('ca_url', 'https://localhost:9000')
        self.provisioner = config.get('provisioner', 'patchman')
        self.password_file = config.get('provisioner_password_file')
        self.root_cert = config.get('root_cert')  # CA root certificate

    def is_available(self) -> bool:
        """Check if step CLI is available."""
        try:
            result = subprocess.run(
                ['step', 'version'],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def sign_csr(self, csr_pem: str, hostname: str, validity_days: int) -> tuple[str, str]:
        if not self.is_available():
            raise PKIError('step CLI is not available')

        csr_file = None
        crt_file = None

        try:
            # Write CSR to temp file
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.csr', delete=False
            ) as f:
                f.write(csr_pem)
                csr_file = f.name

            # Create temp file for output cert
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.crt', delete=False
            ) as f:
                crt_file = f.name

            # Build command
            cmd = [
                'step', 'ca', 'sign',
                '--ca-url', self.ca_url,
                '--provisioner', self.provisioner,
                '--not-after', f'{validity_days * 24}h',
            ]

            if self.password_file:
                cmd.extend(['--provisioner-password-file', self.password_file])

            if self.root_cert:
                cmd.extend(['--root', self.root_cert])

            cmd.extend([csr_file, crt_file])

            logger.debug(f'Running step-ca sign: {" ".join(cmd)}')

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f'step-ca signing failed: {result.stderr}')
                raise PKIError(f'step-ca signing failed: {result.stderr}')

            # Read signed certificate
            with open(crt_file) as f:
                cert_pem = f.read()

            # Extract serial number from certificate
            serial = self._extract_serial(cert_pem)

            return cert_pem, serial

        except subprocess.TimeoutExpired:
            raise PKIError('step-ca signing timed out')
        except Exception as e:
            if isinstance(e, PKIError):
                raise
            raise PKIError(f'step-ca signing error: {e}')
        finally:
            # Clean up temp files
            if csr_file and os.path.exists(csr_file):
                os.unlink(csr_file)
            if crt_file and os.path.exists(crt_file):
                os.unlink(crt_file)

    def _extract_serial(self, cert_pem: str) -> str:
        """Extract serial number from certificate PEM."""
        try:
            from cryptography import x509
            cert = x509.load_pem_x509_certificate(cert_pem.encode())
            return format(cert.serial_number, 'x')
        except ImportError:
            # Fallback: use step CLI
            with tempfile.NamedTemporaryFile(mode='w', suffix='.crt', delete=False) as f:
                f.write(cert_pem)
                crt_file = f.name

            try:
                result = subprocess.run(
                    ['step', 'certificate', 'inspect', '--format', 'json', crt_file],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    import json
                    data = json.loads(result.stdout)
                    return data.get('serial_number', 'unknown')
            finally:
                os.unlink(crt_file)

            return 'unknown'


class VaultProvider(PKIProvider):
    """PKI provider using HashiCorp Vault."""

    def __init__(self):
        config = getattr(settings, 'PKI_PROVIDER_CONFIG', {})
        self.vault_addr = config.get('vault_addr')
        self.pki_path = config.get('pki_path', 'pki')
        self.pki_role = config.get('pki_role', 'patchman-client')

        # Token can come from file or direct config
        token_file = config.get('vault_token_file')
        if token_file and os.path.exists(token_file):
            with open(token_file) as f:
                self.token = f.read().strip()
        else:
            self.token = config.get('vault_token', '')

    def is_available(self) -> bool:
        """Check if Vault is configured and reachable."""
        if not self.vault_addr or not self.token:
            return False

        try:
            import requests
            response = requests.get(
                f'{self.vault_addr}/v1/sys/health',
                headers={'X-Vault-Token': self.token},
                timeout=5,
            )
            return response.status_code in (200, 429, 472, 473)
        except Exception:
            return False

    def sign_csr(self, csr_pem: str, hostname: str, validity_days: int) -> tuple[str, str]:
        if not self.is_available():
            raise PKIError('Vault is not available or not configured')

        try:
            import requests
        except ImportError:
            raise PKIError('requests library required for Vault provider')

        url = f'{self.vault_addr}/v1/{self.pki_path}/sign/{self.pki_role}'
        headers = {'X-Vault-Token': self.token}
        data = {
            'csr': csr_pem,
            'common_name': hostname,
            'ttl': f'{validity_days * 24}h',
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=30,
            )
            response.raise_for_status()

            result = response.json()
            cert_pem = result['data']['certificate']
            serial = result['data']['serial_number']

            # Include CA chain if provided
            if 'ca_chain' in result['data']:
                cert_pem = cert_pem + '\n' + '\n'.join(result['data']['ca_chain'])

            return cert_pem, serial

        except requests.RequestException as e:
            raise PKIError(f'Vault signing failed: {e}')


def get_pki_provider() -> Optional[PKIProvider]:
    """
    Get the configured PKI provider instance.

    Returns None if no provider is configured.
    """
    provider_path = getattr(settings, 'PKI_PROVIDER', None)

    if not provider_path:
        return None

    try:
        module_path, class_name = provider_path.rsplit('.', 1)
        from importlib import import_module
        module = import_module(module_path)
        provider_class = getattr(module, class_name)
        return provider_class()
    except (ImportError, AttributeError, ValueError) as e:
        logger.error(f'Failed to load PKI provider {provider_path}: {e}')
        return None
