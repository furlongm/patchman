# Copyright 2012 VPAC, http://www.vpac.org
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

from patchman.hosts.models import Host
from patchman.arch.models import MachineArchitecture
from patchman.operatingsystems.models import OS
from patchman.domains.models import Domain

from socket import gethostbyaddr


class Report(models.Model):

    time = models.DateTimeField(auto_now_add=True)
    host = models.CharField(max_length=255, null=True)
    domain = models.CharField(max_length=255, null=True)
    tags = models.CharField(max_length=255, null=True, default='')
    kernel = models.CharField(max_length=255, null=True)
    arch = models.CharField(max_length=255, null=True)
    os = models.CharField(max_length=255, null=True)
    report_ip = models.IPAddressField(null=True)
    protocol = models.CharField(max_length=255, null=True)
    useragent = models.CharField(max_length=255, null=True)
    processed = models.BooleanField(default=False)
    packages = models.TextField(null=True, blank=True)
    repos = models.TextField(null=True, blank=True)
    reboot = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ('-time',)

    def __unicode__(self):
        return '%s %s' % (self.host, self.time)

    @models.permalink
    def get_absolute_url(self):
        return ('report_detail', [self.id])

    def parse(self, data, meta):

        self.report_ip = meta['REMOTE_ADDR']
        self.useragent = meta['HTTP_USER_AGENT']

        if 'arch' in data:
            self.arch = data['arch']

        if 'host' in data:
            self.host = data['host']
            fqdn = self.host.split('.', 1)
            self.domain = fqdn.pop()

        if 'os' in data:
            self.os = data['os']

        if 'kernel' in data:
            self.kernel = data['kernel']

        if 'tags' in data:
            self.tags = data['tags']

        if 'protocol' in data:
            self.protocol = data['protocol']

        if 'packages' in data:
            self.packages = data['packages']

        if 'repos' in data:
            self.repos = data['repos']

        if 'reboot' in data:
            self.reboot = data['reboot']

        self.save()

    def process(self):
        if self.os and self.kernel and self.arch:
            os, c = OS.objects.get_or_create(name=self.os)
            arch, c = MachineArchitecture.objects.get_or_create(name=self.arch)

            if not self.domain:
                self.domain = 'unknown'

            domain, c = Domain.objects.get_or_create(name=self.domain)

            if not self.host:
                try:
                    self.host = str(gethostbyaddr(self.report_ip)[0])
                except:
                    self.host = self.report_ip

            host, c = Host.objects.get_or_create(
                hostname=self.host,
                defaults={
                    'ipaddress': self.report_ip,
                    'arch': arch,
                    'os': os,
                    'domain': domain,
                    'lastreport': self.time,
                })

            host.ipaddress = self.report_ip
            host.kernel = self.kernel
            host.arch = arch
            host.os = os
            host.domain = domain
            host.lastreport = self.time
            host.tags = self.tags
# TODO: fix this to record the history of installed
# packages on a host.
            from patchman.reports.utils import process_packages, process_repos
            host.packages.clear()
            process_packages(report=self, host=host)
            # only clear repos if we have a new list
            # apt and yum plugins don't send repos
            if self.repos:
                host.repos.clear()
                process_repos(report=self, host=host)
            if self.reboot == 'True':
                host.reboot_required = True
            else:
                host.reboot_required = False
            host.save()
            self.processed = True
            self.save()
            host.find_updates()
