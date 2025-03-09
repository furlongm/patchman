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

import json
import re
from time import sleep

from django.db import models
from django.urls import reverse

from security.managers import CVEManager
from util import get_url, fetch_content, tz_aware_datetime, error_message


class Reference(models.Model):

    ref_type = models.CharField(max_length=255)
    url = models.URLField(max_length=2000)

    class Meta:
        unique_together = ['ref_type', 'url']

    def __str__(self):
        return self.url


class CWE(models.Model):

    cwe_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, default='')

    def __str__(self):
        return f'{self.cwe_id} - {self.name}'

    def get_absolute_url(self):
        return reverse('security:cwe_detail', args=[self.cwe_id])

    @property
    def int_id(self):
        return int(self.cwe_id.split('-')[1])

    def fetch_cwe_data(self):
        int_id = self.int_id
        mitre_cwe_url = f'https://cwe-api.mitre.org/api/v1/cwe/{int_id}'
        res = get_url(mitre_cwe_url)
        data = fetch_content(res, f'Fetching {self.cwe_id} data')
        cwe_json = json.loads(data)
        if cwe_json == 'at least one CWE not found':
            return
        cwe = cwe_json[0]
        if cwe.get('Type').endswith('weakness'):
            weakness_url = f'https://cwe-api.mitre.org/api/v1/cwe/weakness/{int_id}'
            res = get_url(weakness_url)
            data = fetch_content(res, f'Fetching {self.cwe_id} weakness data')
            weakness_json = json.loads(data)
            for weakness in weakness_json.get('Weaknesses'):
                if int(weakness.get('ID')) == int_id:
                    self.name = weakness.get('Name')
                    self.description = weakness.get('Description')
                    self.save()


class CVSS(models.Model):

    score = models.DecimalField(max_digits=3, decimal_places=1, null=True)
    severity = models.CharField(max_length=255, blank=True, null=True)
    version = models.DecimalField(max_digits=2, decimal_places=1)
    vector_string = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.score} ({self.severity}) [{self.vector_string}]'


class CVE(models.Model):

    cve_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, default='')
    reserved_date = models.DateTimeField(blank=True, null=True)
    published_date = models.DateTimeField(blank=True, null=True)
    rejected_date = models.DateTimeField(blank=True, null=True)
    updated_date = models.DateTimeField(blank=True, null=True)
    cwes = models.ManyToManyField(CWE, blank=True)
    cvss_scores = models.ManyToManyField(CVSS, blank=True)
    references = models.ManyToManyField(Reference, blank=True)

    objects = CVEManager()

    class Meta:
        ordering = ['-cve_id']

    def __str__(self):
        return self.cve_id

    def get_absolute_url(self):
        return reverse('security:cve_detail', args=[self.cve_id])

    def fetch_cve_data(self, fetch_nist_data=False, sleep_secs=6):
        self.fetch_mitre_cve_data()
        if fetch_nist_data:
            self.fetch_nist_cve_data()
            sleep(sleep_secs)  # rate limited, see https://nvd.nist.gov/developers/start-here

    def fetch_mitre_cve_data(self):
        mitre_cve_url = f'https://cveawg.mitre.org/api/cve/{self.cve_id}'
        res = get_url(mitre_cve_url)
        if res.status_code == 404:
            error_message.send(sender=None, text=f'404 - Skipping {self.cve_id} - {mitre_cve_url}')
            return
        data = fetch_content(res, f'Fetching {self.cve_id} MITRE data')
        cve_json = json.loads(data)
        self.parse_mitre_cve_data(cve_json)

    def fetch_nist_cve_data(self):
        nist_cve_url = f'https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={self.cve_id}'
        res = get_url(nist_cve_url)
        data = fetch_content(res, f'Fetching {self.cve_id} NIST data')
        if res.status_code == 404:
            error_message.send(sender=None, text=f'404 - Skipping {self.cve_id} - {nist_cve_url}')
        cve_json = json.loads(data)
        self.parse_nist_cve_data(cve_json)

    def parse_nist_cve_data(self, cve_json):
        from security.utils import get_or_create_reference
        vulnerabilites = cve_json.get('vulnerabilities')
        for vulnerability in vulnerabilites:
            cve = vulnerability.get('cve')
            cve_id = cve.get('id')
            if cve_id != self.cve_id:
                error_message.send(sender=None, text=f'CVE ID mismatch - {self.cve_id} - {cve_id}')
                return
            metrics = cve.get('metrics')
            for metric, score_data in metrics.items():
                if metric.startswith('cvss'):
                    for scores in score_data:
                        for key, value in scores.items():
                            if key.startswith('cvssData'):
                                cvss_score, created = CVSS.objects.get_or_create(
                                    score=value.get('baseScore'),
                                    severity=value.get('baseSeverity'),
                                    version=value.get('version'),
                                    vector_string=value.get('vectorString'),
                                )
                                self.cvss_scores.add(cvss_score)
            references = cve.get('references')
            for reference in references:
                ref_type = 'Link'
                url = reference.get('url')
                ref = get_or_create_reference(ref_type=ref_type, url=url)
                self.references.add(ref)

    def parse_mitre_cve_data(self, cve_json):
        cve_metadata = cve_json.get('cveMetadata')
        reserved_date = cve_metadata.get('dateReserved')
        if reserved_date:
            self.reserved_date = tz_aware_datetime(cve_metadata.get('dateReserved'))
        rejected_date = cve_metadata.get('dateRejected')
        if rejected_date:
            self.rejected_date = tz_aware_datetime(rejected_date)
        published_date = cve_metadata.get('datePublished')
        if published_date:
            self.published_date = tz_aware_datetime(cve_metadata.get('datePublished'))
        updated_date = cve_metadata.get('dateUpdated')
        if updated_date:
            self.updated_date = tz_aware_datetime(cve_metadata.get('dateUpdated'))
        cna_container = cve_json.get('containers').get('cna')
        title = cna_container.get('title')
        if not title:
            product = cna_container.get('product')
        descriptions = cna_container.get('descriptions')
        if descriptions:
            self.description = descriptions[0].get('value')
        problem_types = cna_container.get('problemTypes', [])
        for problem_type in problem_types:
            descriptions = problem_type.get('descriptions')
            if descriptions:
                for description in descriptions:
                    cwe_description = description.get('description')
                    if description.get('type') == 'CWE':
                        cwe_id = description.get('cweId')
                        if cwe_id:
                            cwe, created = CWE.objects.get_or_create(cwe_id=cwe_id)
                            self.cwes.add(cwe)
                    cwe_ids = re.findall(r'CWE-\d+', cwe_description)
                    for cwe_id in cwe_ids:
                        cwe, created = CWE.objects.get_or_create(cwe_id=cwe_id)
                        self.cwes.add(cwe)
        if not title:
            if product and cwe_description:
                self.title = f'{product} - {cwe_description}'
            else:
                self.title = ''
        metrics = cna_container.get('metrics')
        if metrics:
            for metric in metrics:
                if metric.get('format') == 'CVSS':
                    for key, value in metric.items():
                        if key.startswith('cvss'):
                            cvss_score, created = CVSS.objects.get_or_create(
                                score=value.get('baseScore'),
                                severity=value.get('baseSeverity'),
                                version=value.get('version'),
                                vector_string=value.get('vectorString'),
                            )
                            self.cvss_scores.add(cvss_score)
        self.save()
