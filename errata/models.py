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

from django.db import models
from django.urls import reverse
from django.db import IntegrityError

from packages.models import Package, PackageUpdate
from packages.utils import find_evr, get_matching_packages
from errata.managers import ErratumManager
from security.models import CVE, Reference
from security.utils import get_or_create_cve, get_or_create_reference
from util.logging import error_message
from util import get_url


class Erratum(models.Model):

    name = models.CharField(max_length=255, unique=True)
    e_type = models.CharField(max_length=255)
    issue_date = models.DateTimeField()
    synopsis = models.CharField(max_length=255)
    affected_packages = models.ManyToManyField(Package, blank=True, related_name='affected_by_erratum')
    fixed_packages = models.ManyToManyField(Package, blank=True, related_name='provides_fix_in_erratum')
    from operatingsystems.models import OSRelease
    osreleases = models.ManyToManyField(OSRelease, blank=True)
    cves = models.ManyToManyField(CVE, blank=True)
    references = models.ManyToManyField(Reference, blank=True)

    objects = ErratumManager()

    class Meta:
        verbose_name = 'Erratum'
        verbose_name_plural = 'Errata'
        ordering = ['-issue_date', 'name']

    def __str__(self):
        text = f'{self.name} ({self.e_type}), {self.cves.count()} related CVEs, '
        text += f'affecting {self.osreleases.count()} OS Releases, '
        text += f'providing {self.fixed_packages.count()} fixed Packages'
        return text

    def get_absolute_url(self):
        return reverse('errata:erratum_detail', args=[self.name])

    def scan_for_security_updates(self):
        if self.e_type == 'security':
            for package in self.fixed_packages.all():
                affected_updates = PackageUpdate.objects.filter(
                    newpackage=package,
                    security=False,
                )
                for affected_update in affected_updates:
                    affected_update.security = True
                    try:
                        affected_update.save()
                    except IntegrityError as e:
                        error_message(text=e)
                        # a version of this update already exists that is
                        # marked as a security update, so delete this one
                        affected_update.delete()
            for package in self.affected_packages.all():
                affected_updates = PackageUpdate.objects.filter(
                    oldpackage=package,
                    security=False,
                )
                for affected_update in affected_updates:
                    affected_update.security = True
                    try:
                        affected_update.save()
                    except IntegrityError as e:
                        error_message(text=e)
                        # a version of this update already exists that is
                        # marked as a security update, so delete this one
                        affected_update.delete()

    def fetch_osv_dev_data(self):
        osv_dev_url = f'https://api.osv.dev/v1/vulns/{self.name}'
        res = get_url(osv_dev_url)
        if res.status_code == 404:
            error_message(text=f'404 - Skipping {self.name} - {osv_dev_url}')
            return
        data = res.content
        osv_dev_json = json.loads(data)
        self.parse_osv_dev_data(osv_dev_json)

    def parse_osv_dev_data(self, osv_dev_json):
        name = osv_dev_json.get('id')
        if name != self.name:
            error_message(text=f'Erratum name mismatch - {self.name} != {name}')
            return
        related = osv_dev_json.get('related')
        if related:
            for vuln in related:
                if vuln.startswith('CVE'):
                    self.add_cve(vuln)
        affected = osv_dev_json.get('affected')
        if not affected:
            return
        affected_packages = set()
        for package in affected:
            fixed_packages = set()
            ranges = package.get('ranges')
            for affected_range in ranges:
                for event in affected_range.get('events'):
                    fixed_version = event.get('fixed')
                    if fixed_version:
                        epoch, ver, rel = find_evr(fixed_version)
                        matching_packages = self.fixed_packages.filter(epoch=epoch, version=ver, release=rel).all()
                        for match in matching_packages:
                            fixed_packages.add(match)
            affected_versions = package.get('versions')
            if not affected_versions:
                continue
            for package in fixed_packages:
                for version in affected_versions:
                    epoch, ver, rel = find_evr(version)
                    matching_packages = get_matching_packages(
                        name=package.name,
                        epoch=epoch,
                        version=ver,
                        release=rel,
                        arch=package.arch,
                        p_type=package.packagetype,
                    )
                    for match in matching_packages:
                        affected_packages.add(match)
        self.add_affected_packages(affected_packages)

    def add_fixed_packages(self, packages):
        for package in packages:
            self.fixed_packages.add(package)
        self.save()

    def add_affected_packages(self, packages):
        for package in packages:
            self.affected_packages.add(package)

    def add_cve(self, cve_id):
        """ Add a CVE to an Erratum object
        """
        if not cve_id.startswith('CVE') or not cve_id.split('-')[1].isdigit():
            error_message(text=f'Not a CVE ID: {cve_id}')
            return
        self.cves.add(get_or_create_cve(cve_id))

    def add_reference(self, ref_type, url):
        """ Add a reference to an Erratum object
        """
        reference = get_or_create_reference(ref_type=ref_type, url=url)
        self.references.add(reference)
