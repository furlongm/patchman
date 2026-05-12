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

from django.db import models


class ComplianceProfile(models.Model):

    profile_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=512, blank=True, default='')
    description = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['profile_id']

    def __str__(self):
        return self.profile_id


class ComplianceRule(models.Model):

    rule_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=512, blank=True, default='')
    severity = models.CharField(max_length=32, blank=True, default='')
    description = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['rule_id']

    def __str__(self):
        return self.rule_id


class ComplianceScan(models.Model):

    host = models.ForeignKey(
        'hosts.Host',
        on_delete=models.CASCADE,
        related_name='compliance_scans',
    )
    profile = models.ForeignKey(
        ComplianceProfile,
        on_delete=models.CASCADE,
        related_name='scans',
    )
    datastream = models.CharField(max_length=255, blank=True, default='')
    score = models.FloatField(default=0.0)
    score_maximum = models.FloatField(default=100.0)
    pass_count = models.IntegerField(default=0)
    fail_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    notapplicable_count = models.IntegerField(default=0)
    scanned_at = models.DateTimeField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scanned_at']
        constraints = [
            models.UniqueConstraint(
                fields=['host', 'profile', 'scanned_at'],
                name='unique_compliance_scan',
            ),
        ]

    def __str__(self):
        return f'{self.host} - {self.profile} @ {self.scanned_at}'


class ComplianceResult(models.Model):

    RESULT_CHOICES = [
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('error', 'Error'),
        ('notapplicable', 'Not Applicable'),
        ('notchecked', 'Not Checked'),
        ('notselected', 'Not Selected'),
        ('informational', 'Informational'),
        ('fixed', 'Fixed'),
    ]

    scan = models.ForeignKey(
        ComplianceScan,
        on_delete=models.CASCADE,
        related_name='results',
    )
    rule = models.ForeignKey(
        ComplianceRule,
        on_delete=models.CASCADE,
        related_name='results',
    )
    result = models.CharField(max_length=32, choices=RESULT_CHOICES)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['scan', 'rule'],
                name='unique_compliance_result',
            ),
        ]
        indexes = [
            models.Index(fields=['rule', 'result']),
        ]

    def __str__(self):
        return f'{self.rule} - {self.result}'
