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

from django.contrib import admin

from patchman.compliance.models import (
    ComplianceProfile, ComplianceResult, ComplianceRule, ComplianceScan,
)


@admin.register(ComplianceProfile)
class ComplianceProfileAdmin(admin.ModelAdmin):
    list_display = ('profile_id', 'title')
    search_fields = ('profile_id', 'title', 'description')


@admin.register(ComplianceRule)
class ComplianceRuleAdmin(admin.ModelAdmin):
    list_display = ('rule_id', 'title', 'severity')
    list_filter = ('severity',)
    search_fields = ('rule_id', 'title', 'description')


@admin.register(ComplianceScan)
class ComplianceScanAdmin(admin.ModelAdmin):
    list_display = (
        'host', 'profile', 'score', 'pass_count',
        'fail_count', 'error_count', 'scanned_at',
    )
    list_filter = ('profile', 'scanned_at')
    search_fields = ('host__hostname', 'profile__profile_id')
    raw_id_fields = ('host', 'profile')


@admin.register(ComplianceResult)
class ComplianceResultAdmin(admin.ModelAdmin):
    list_display = ('scan', 'rule', 'result')
    list_filter = ('result',)
    search_fields = ('rule__rule_id', 'scan__host__hostname')
    raw_id_fields = ('scan', 'rule')
