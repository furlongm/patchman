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

import fnmatch
import secrets

from django.db import models
from django.utils import timezone


def generate_enrollment_token():
    """Generate a secure enrollment token."""
    return f'enroll_{secrets.token_urlsafe(32)}'


class EnrollmentToken(models.Model):
    """One-time token for client certificate enrollment."""

    token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_enrollment_token,
    )
    hostname_pattern = models.CharField(
        max_length=255,
        blank=True,
        help_text='Glob pattern for allowed hostnames (e.g., "*.example.com"). Empty = any.',
    )
    created = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField()
    single_use = models.BooleanField(default=True)
    used_by = models.CharField(max_length=255, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        status = 'used' if self.used_by else ('expired' if self.is_expired else 'active')
        return f'{self.token[:20]}... ({status})'

    @property
    def is_expired(self):
        return self.expires < timezone.now()

    @property
    def is_valid(self):
        if self.is_expired:
            return False
        if self.single_use and self.used_by:
            return False
        return True

    def matches_hostname(self, hostname):
        """Check if hostname matches the allowed pattern."""
        if not self.hostname_pattern:
            return True
        return fnmatch.fnmatch(hostname, self.hostname_pattern)

    def mark_used(self, hostname):
        self.used_by = hostname
        self.used_at = timezone.now()
        self.save(update_fields=['used_by', 'used_at'])


class ClientCertificate(models.Model):
    """Track issued client certificates."""

    hostname = models.CharField(max_length=255, db_index=True)
    serial_number = models.CharField(max_length=64, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=255, blank=True)
    enrollment_token = models.ForeignKey(
        EnrollmentToken,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certificates',
    )

    class Meta:
        ordering = ['-issued_at']

    def __str__(self):
        status = 'revoked' if self.revoked else (
            'expired' if self.expires_at < timezone.now() else 'active'
        )
        return f'{self.hostname} ({status})'

    @property
    def is_valid(self):
        if self.revoked:
            return False
        if self.expires_at < timezone.now():
            return False
        return True

    def revoke(self, reason=''):
        self.revoked = True
        self.revoked_at = timezone.now()
        self.revoked_reason = reason
        self.save(update_fields=['revoked', 'revoked_at', 'revoked_reason'])
