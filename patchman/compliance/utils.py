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

from django.utils.dateparse import parse_datetime

from patchman.compliance.models import (
    ComplianceProfile, ComplianceResult, ComplianceRule, ComplianceScan,
)


def process_compliance_json(compliance_json, host):
    """Process compliance scan JSON and create/update models."""

    profile_id = compliance_json.get('profile', '')
    profile, _ = ComplianceProfile.objects.get_or_create(
        profile_id=profile_id,
    )

    scan_time_str = compliance_json.get('start_time') or compliance_json.get('scan_date')
    scan_time = parse_datetime(scan_time_str) if scan_time_str else None
    if scan_time is None:
        return

    summary = compliance_json.get('summary', {})

    scan, created = ComplianceScan.objects.get_or_create(
        host=host,
        profile=profile,
        scanned_at=scan_time,
        defaults={
            'datastream': compliance_json.get('datastream', ''),
            'score': compliance_json.get('score', 0.0),
            'score_maximum': compliance_json.get('score_maximum', 100.0),
            'pass_count': summary.get('pass', 0),
            'fail_count': summary.get('fail', 0),
            'error_count': summary.get('error', 0),
            'notapplicable_count': summary.get('notapplicable', 0),
        },
    )
    if not created:
        return  # already processed

    rules_data = compliance_json.get('rules', [])
    rules_to_create = {}
    for r in rules_data:
        rule_id = r.get('id', '')
        if rule_id and rule_id not in rules_to_create:
            rules_to_create[rule_id] = {
                'severity': r.get('severity', ''),
            }

    # bulk get_or_create rules
    existing = {
        r.rule_id: r
        for r in ComplianceRule.objects.filter(rule_id__in=rules_to_create.keys())
    }
    new_rules = []
    for rule_id, data in rules_to_create.items():
        if rule_id not in existing:
            new_rules.append(
                ComplianceRule(rule_id=rule_id, severity=data['severity'])
            )
    if new_rules:
        ComplianceRule.objects.bulk_create(new_rules, ignore_conflicts=True)
        existing = {
            r.rule_id: r
            for r in ComplianceRule.objects.filter(
                rule_id__in=rules_to_create.keys()
            )
        }

    # bulk create results
    results = []
    for r in rules_data:
        rule = existing.get(r.get('id', ''))
        if rule:
            results.append(
                ComplianceResult(
                    scan=scan,
                    rule=rule,
                    result=r.get('result', 'notchecked'),
                )
            )
    if results:
        ComplianceResult.objects.bulk_create(results, ignore_conflicts=True)
