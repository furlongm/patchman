# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2021 Marcus Furlong <furlongm@gmail.com>
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

import re

from django.db import models, IntegrityError, DatabaseError, transaction
from django.urls import reverse

from arch.models import MachineArchitecture
from hosts.models import Host
from operatingsystems.models import OSVariant, OSRelease
from domains.models import Domain
from patchman.signals import error_message, info_message

from socket import gethostbyaddr, herror


class Report(models.Model):

    created = models.DateTimeField(auto_now_add=True)
    accessed = models.DateTimeField(auto_now_add=True)
    host = models.CharField(max_length=255, null=True)
    domain = models.CharField(max_length=255, null=True)
    tags = models.CharField(max_length=255, null=True, default='')
    kernel = models.CharField(max_length=255, null=True)
    arch = models.CharField(max_length=255, null=True)
    os = models.CharField(max_length=255, null=True)
    report_ip = models.GenericIPAddressField(null=True, blank=True)
    protocol = models.CharField(max_length=255, null=True)
    useragent = models.CharField(max_length=255, null=True)
    processed = models.BooleanField(default=False)
    packages = models.TextField(null=True, blank=True)
    sec_updates = models.TextField(null=True, blank=True)
    bug_updates = models.TextField(null=True, blank=True)
    repos = models.TextField(null=True, blank=True)
    modules = models.TextField(null=True, blank=True)
    reboot = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Report'
        verbose_name_plural = 'Reports'
        ordering = ('-created',)

    def __str__(self):
        return f"{self.host} {self.created.strftime('%c')}"

    def get_absolute_url(self):
        return reverse('reports:report_detail', args=[str(self.id)])

    def parse(self, data, meta):
        """ Parse a report and save the object
        """
        x_real_ip = meta.get('HTTP_X_REAL_IP')
        x_forwarded_for = meta.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            self.report_ip = x_forwarded_for.split(',')[0]
        elif x_real_ip:
            self.report_ip = x_real_ip
        else:
            self.report_ip = meta['REMOTE_ADDR']
        self.useragent = meta['HTTP_USER_AGENT']
        self.domain = None

        attrs = ['arch',
                 'host',
                 'os',
                 'kernel',
                 'protocol',
                 'packages',
                 'tags',
                 'sec_updates',
                 'bug_updates',
                 'repos',
                 'modules',
                 'reboot']

        for attr in attrs:
            if data.get(attr):
                setattr(self, attr, data.get(attr))
            else:
                setattr(self, attr, '')

        if self.host:
            self.host = self.host.lower()
            fqdn = self.host.split('.', 1)
            if len(fqdn) == 2:
                self.domain = fqdn.pop()

        with transaction.atomic():
            self.save()

    def process(self, find_updates=True, verbose=False):
        """ Process a report and extract os, arch, domain, packages, repos etc
        """
        if self.os and self.kernel and self.arch and not self.processed:
            os = self.os
            cpe_name = None
            codename = None
            osrelease_codename = None
            osvariant_codename = None
            osrelease_name = os
            osvariant_name = os

            # find cpe_name if it exists
            match = re.match(r'(.*) \[(.*)\]', os)
            if match:
                cpe_name = match.group(2)
                os = match.group(1)

            # find codename if it exists
            match = re.match(r'(.*) \((.*)\)', os)
            if match:
                osrelease_name = match.group(1)
                codename = match.group(2)
                if not os.startswith('AlmaLinux'):
                    osrelease_codename = codename

            if os.startswith('Gentoo'):
                osrelease_name = 'Gentoo Linux'
                # presumptive, can be changed once a real cpe is assigned/used
                cpe_name = 'cpe:2.3:o:gentoo:gentoo_linux:::'

            if os.startswith('AlmaLinux'):
                os = os.replace('AlmaLinux', 'Alma Linux')
                osrelease_name = os.split('.')[0]
                # alma changes the codename with each minor release, so it's useless to us now
                osvariant_name = os.replace(f' ({codename})', '')
                osvariant_codename = codename

            if os.startswith('Debian'):
                major, minor = os.split(' ')[1].split('.')
                debian_version = f'{major}.{minor}'
                osrelease_name = f'Debian {major}'
                # presumptive, can be changed once a real cpe is assigned/used
                cpe_name = f'cpe:2.3:o:debian:debian_linux:{debian_version}::'

            if os.startswith('Ubuntu'):
                lts = ''
                if 'LTS' in os:
                    lts = ' LTS'
                major, minor, patch = os.split(' ')[1].split('.')
                ubuntu_version = f'{major}_{minor}'
                osrelease_name = f'Ubuntu {major}.{minor}{lts}'
                cpe_name = f'cpe:2.3:o:canonical:ubuntu_linux:{ubuntu_version}::'

            if os.startswith('Arch'):
                # presumptive, can be changed once a real cpe is assigned/used
                cpe_name = 'cpe:2.3:o:archlinux:arch_linux:::'

            if os.startswith('Rocky'):
                osrelease_name = os.split('.')[0]

            with transaction.atomic():
                m_arch, created = MachineArchitecture.objects.get_or_create(name=self.arch)

            with transaction.atomic():
                try:
                    osvariant, created = OSVariant.objects.get_or_create(name=osvariant_name, arch=m_arch)
                except IntegrityError:
                    osvariants = OSVariant.objects.filter(name=osvariant_name)
                    if osvariants.count() == 1:
                        osvariant = osvariants[0]
                        if osvariant.arch is None:
                            osvariant.arch = m_arch

            if osvariant and osvariant_codename:
                osvariant.codename = osvariant_codename

            if cpe_name:
                try:
                    osrelease, created = OSRelease.objects.get_or_create(name=osrelease_name, cpe_name=cpe_name)
                except IntegrityError:
                    osreleases = OSRelease.objects.filter(name=osrelease_name)
                    if osreleases.count() == 1:
                        osrelease = osreleases[0]
                        osrelease.cpe_name = cpe_name
            elif osrelease_codename:
                osreleases = OSRelease.objects.filter(codename=osrelease_codename)
                if osreleases.count() == 1:
                    osrelease = osreleases[0]
            elif osrelease_name:
                osrelease, created = OSRelease.objects.get_or_create(name=osrelease_name)
            osrelease.save()
            osvariant.osrelease = osrelease
            osvariant.save()

            if not self.domain:
                self.domain = 'unknown'
            domains = Domain.objects.all()
            with transaction.atomic():
                domain, c = domains.get_or_create(name=self.domain)

            if not self.host:
                try:
                    self.host = str(gethostbyaddr(self.report_ip)[0])
                except herror:
                    self.host = self.report_ip

            with transaction.atomic():
                host, c = Host.objects.get_or_create(
                    hostname=self.host,
                    defaults={
                        'ipaddress': self.report_ip,
                        'arch': m_arch,
                        'osvariant': osvariant,
                        'domain': domain,
                        'lastreport': self.created,
                    })

            host.ipaddress = self.report_ip
            host.kernel = self.kernel
            host.arch = m_arch
            host.osvariant = osvariant
            host.domain = domain
            host.lastreport = self.created
            host.tags = self.tags
            if self.reboot == 'True':
                host.reboot_required = True
            else:
                host.reboot_required = False
            try:
                with transaction.atomic():
                    host.save()
            except IntegrityError as e:
                error_message.send(sender=None, text=e)
            except DatabaseError as e:
                error_message.send(sender=None, text=e)
            host.check_rdns()

            if verbose:
                text = 'Processing report {self.id} - {self.host}'
                info_message.send(sender=None, text=text)

            from reports.utils import process_packages, process_repos, process_updates, process_modules
            with transaction.atomic():
                process_repos(report=self, host=host)
            with transaction.atomic():
                process_modules(report=self, host=host)
            with transaction.atomic():
                process_packages(report=self, host=host)
            with transaction.atomic():
                process_updates(report=self, host=host)

            self.processed = True
            with transaction.atomic():
                self.save()

            if find_updates:
                if verbose:
                    text = 'Finding updates for report {self.id} - {self.host}'
                    info_message.send(sender=None, text=text)
                host.find_updates()
        else:
            if self.processed:
                text = f'Report {self.id} has already been processed'
                info_message.send(sender=None, text=text)
            else:
                text = 'Error: OS, kernel or arch not sent with report {self.id}'
                error_message.send(sender=None, text=text)
