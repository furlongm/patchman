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

from django.db import models
from django.urls import reverse

from hosts.utils import get_or_create_host
from util.logging import error_message, info_message


class Report(models.Model):

    created = models.DateTimeField(auto_now_add=True)
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
        ordering = ['-created']

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
        self.save()

    def process(self, find_updates=True, verbose=False):
        """ Process a report and extract os, arch, domain, packages, repos etc
        """
        if not self.os or not self.kernel or not self.arch:
            error_message(text=f'Error: OS, kernel or arch not sent with report {self.id}')
            return

        if self.processed:
            info_message(text=f'Report {self.id} has already been processed')
            return

        from reports.utils import get_arch, get_os, get_domain
        arch = get_arch(self.arch)
        osvariant = get_os(self.os, arch)
        domain = get_domain(self.domain)
        host = get_or_create_host(self, arch, osvariant, domain)

        if verbose:
            info_message(text=f'Processing report {self.id} - {self.host}')

        from reports.utils import process_packages, process_repos, process_updates, process_modules
        process_repos(report=self, host=host)
        process_modules(report=self, host=host)
        process_packages(report=self, host=host)
        process_updates(report=self, host=host)

        self.processed = True
        self.save()

        if find_updates:
            if verbose:
                info_message(text=f'Finding updates for report {self.id} - {self.host}')
            host.find_updates()
