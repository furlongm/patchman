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

from rest_framework import serializers

from util.models import ClientCertificate, EnrollmentToken


class EnrollmentTokenSerializer(serializers.ModelSerializer):
    """Serializer for enrollment tokens (admin view)."""

    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = EnrollmentToken
        fields = [
            'id', 'token', 'hostname_pattern', 'created', 'expires',
            'single_use', 'used_by', 'used_at', 'created_by', 'notes',
            'is_valid', 'is_expired',
        ]
        read_only_fields = ['id', 'token', 'created', 'used_by', 'used_at']


class ClientCertificateSerializer(serializers.ModelSerializer):
    """Serializer for client certificates."""

    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = ClientCertificate
        fields = [
            'id', 'hostname', 'serial_number', 'issued_at', 'expires_at',
            'revoked', 'revoked_at', 'revoked_reason', 'is_valid',
        ]


class EnrollRequestSerializer(serializers.Serializer):
    """Serializer for certificate enrollment request."""

    token = serializers.CharField(max_length=64)
    csr = serializers.CharField()
    hostname = serializers.CharField(max_length=255)


class EnrollResponseSerializer(serializers.Serializer):
    """Serializer for certificate enrollment response."""

    certificate = serializers.CharField()
    serial_number = serializers.CharField()
    expires_in_days = serializers.IntegerField()


class RenewRequestSerializer(serializers.Serializer):
    """Serializer for certificate renewal request."""

    csr = serializers.CharField()


class RenewResponseSerializer(serializers.Serializer):
    """Serializer for certificate renewal response."""

    certificate = serializers.CharField()
    serial_number = serializers.CharField()
    expires_in_days = serializers.IntegerField()
