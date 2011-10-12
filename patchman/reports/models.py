# Copyright 2011 VPAC <furlongm@vpac.org>
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

from datetime import datetime, date, time

from patchman.hosts.models import Host
from patchman.arch.models import MachineArchitecture, PackageArchitecture
from patchman.operatingsystems.models import OS
from patchman.domains.models import Domain
from patchman.packages.models import Package, PackageName
from patchman.repos.models import Repository

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

    class Meta:
        ordering = ('-time',)

    def __unicode__(self):
        return '%s %s' % (self.host, self.time)

    def parse (self, data, meta):

        self.report_ip = meta['REMOTE_ADDR']
        self.useragent = meta['HTTP_USER_AGENT']

        if 'arch' in data:
            self.arch=data['arch']

        if 'host' in data:
            self.host=data['host']
            fqdn=self.host.split('.',1)
            self.domain = fqdn.pop()

        if 'os' in data:
            self.os=data['os']

        if 'kernel' in data:
            self.kernel=data['kernel']

        if 'tags' in data:
            self.tags=data['tags']

        if 'protocol' in data:
            self.protocol=data['protocol']

        if 'packages' in data:
            self.packages = data['packages']

        self.save()

    @models.permalink
    def get_absolute_url(self):
        return ('report_detail', [self.id])

