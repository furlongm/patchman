# Copyright 2013-2025 Marcus Furlong <furlongm@gmail.com>
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


class PackageSerializer(serializers.Serializer):
    """Serializer for a single package in a report."""
    name = serializers.CharField(max_length=255)
    epoch = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    version = serializers.CharField(max_length=255)
    release = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    arch = serializers.CharField(max_length=255)
    type = serializers.ChoiceField(choices=['deb', 'rpm', 'arch', 'gentoo'])
    # Gentoo-specific fields
    category = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    repo = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')


class RepoSerializer(serializers.Serializer):
    """Serializer for a single repository in a report."""
    type = serializers.ChoiceField(choices=['deb', 'rpm', 'arch', 'gentoo'])
    name = serializers.CharField(max_length=255)
    id = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    priority = serializers.IntegerField(required=False, default=0)
    urls = serializers.ListField(
        child=serializers.URLField(max_length=512),
        required=False,
        default=list
    )


class ModuleSerializer(serializers.Serializer):
    """Serializer for a single module in a report."""
    name = serializers.CharField(max_length=255)
    stream = serializers.CharField(max_length=255)
    version = serializers.CharField(max_length=255)
    context = serializers.CharField(max_length=255)
    arch = serializers.CharField(max_length=255)
    repo = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    packages = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        default=list
    )


class UpdateSerializer(serializers.Serializer):
    """Serializer for a single update (security or bugfix) in a report."""
    name = serializers.CharField(max_length=255)
    version = serializers.CharField(max_length=255)
    arch = serializers.CharField(max_length=255)
    repo = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')


class ReportUploadSerializer(serializers.Serializer):
    """Serializer for protocol 2 JSON report uploads."""
    protocol = serializers.IntegerField(default=2)
    hostname = serializers.CharField(max_length=255)
    arch = serializers.CharField(max_length=255)
    kernel = serializers.CharField(max_length=255)
    os = serializers.CharField(max_length=255)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        default=list
    )
    reboot_required = serializers.BooleanField(required=False, default=False)
    packages = PackageSerializer(many=True, required=False, default=list)
    repos = RepoSerializer(many=True, required=False, default=list)
    modules = ModuleSerializer(many=True, required=False, default=list)
    sec_updates = UpdateSerializer(many=True, required=False, default=list)
    bug_updates = UpdateSerializer(many=True, required=False, default=list)

    def validate_protocol(self, value):
        if value != 2:
            raise serializers.ValidationError('This endpoint only accepts protocol 2')
        return value


class ReportSerializer(serializers.HyperlinkedModelSerializer):
    """Serializer for reading Report model instances."""

    class Meta:
        from reports.models import Report
        model = Report
        fields = (
            'id', 'host', 'domain', 'tags', 'kernel', 'arch', 'os',
            'report_ip', 'protocol', 'useragent', 'processed', 'created'
        )
