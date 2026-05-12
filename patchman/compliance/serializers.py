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

from rest_framework import serializers

from patchman.compliance.models import (
    ComplianceProfile, ComplianceResult, ComplianceRule, ComplianceScan,
)


class ComplianceProfileSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ComplianceProfile
        fields = ('id', 'profile_id', 'title', 'description')


class ComplianceRuleSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ComplianceRule
        fields = ('id', 'rule_id', 'title', 'severity', 'description')


class ComplianceScanSerializer(serializers.HyperlinkedModelSerializer):
    hostname = serializers.CharField(source='host.hostname', read_only=True)
    profile_id = serializers.CharField(
        source='profile.profile_id', read_only=True,
    )

    class Meta:
        model = ComplianceScan
        fields = (
            'id', 'hostname', 'profile_id', 'datastream',
            'score', 'score_maximum',
            'pass_count', 'fail_count', 'error_count',
            'notapplicable_count', 'scanned_at',
        )


class ComplianceResultSerializer(serializers.HyperlinkedModelSerializer):
    rule_id = serializers.CharField(source='rule.rule_id', read_only=True)
    severity = serializers.CharField(source='rule.severity', read_only=True)

    class Meta:
        model = ComplianceResult
        fields = ('id', 'rule_id', 'severity', 'result')
