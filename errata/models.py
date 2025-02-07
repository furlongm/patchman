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
from django.urls import reverse
from django.db import transaction, IntegrityError

from packages.models import Package, PackageUpdate
from errata.managers import ErratumManager
from security.models import CVE
from security.utils import get_or_create_cve
from patchman.signals import error_message


class ErratumReference(models.Model):

    er_type = models.CharField(max_length=255)
    url = models.URLField(max_length=2000)

    def __str__(self):
        return self.url


class Erratum(models.Model):

    name = models.CharField(max_length=255, unique=True)
    e_type = models.CharField(max_length=255)
    issue_date = models.DateTimeField()
    synopsis = models.CharField(max_length=255)
    packages = models.ManyToManyField(Package, blank=True)
    from operatingsystems.models import OSRelease
    osreleases = models.ManyToManyField(OSRelease, blank=True)
    cves = models.ManyToManyField(CVE, blank=True)
    references = models.ManyToManyField(ErratumReference, blank=True)

    objects = ErratumManager()

    class Meta:
        verbose_name = 'Erratum'
        verbose_name_plural = 'Errata'

    def __str__(self):
        text = f'{self.name!s} ({self.e_type}), {self.cves.count()} related CVEs, '
        text += f'affecting {self.packages.count()} packages and {self.osreleases.count()} OS Releases'
        return text

    def get_absolute_url(self):
        return reverse('errata:erratum_detail', args=[self.name])

    def scan_for_security_updates(self):
        if self.e_type == 'security':
            for package in self.packages.all():
                affected_updates = PackageUpdate.objects.filter(
                    newpackage=package,
                    security=False
                )
                for affected_update in affected_updates:
                    if not affected_update.security:
                        affected_update.security = True
                        try:
                            with transaction.atomic():
                                affected_update.save()
                        except IntegrityError as e:
                            error_message.send(sender=None, text=e)
                            # a version of this update already exists that is
                            # marked as a security update, so delete this one
                            affected_update.delete()

    def add_packages(self, packages):
        for package in packages:
            self.packages.add(package)

    def add_cve(self, cve_id):
        """ Add a CVE to an Erratum object
        """
        self.cves.add(get_or_create_cve(cve_id))

    def add_reference(self, e_type, url):
        """ Add a reference to an Erratum object
        """
        from errata.utils import fixup_erratum_reference
        reference = fixup_erratum_reference({'er_type': e_type, 'url': url})
        if reference:
            with transaction.atomic():
                er, created = ErratumReference.objects.get_or_create(
                    er_type=reference.get('er_type'),
                    url=reference.get('url'),
                )
            self.references.add(er)
