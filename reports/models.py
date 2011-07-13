from django.db import models

from datetime import datetime, date, time

from patchman.hosts.models import Host
from patchman.arch.models import MachineArchitecture, PackageArchitecture
from patchman.operatingsystems.models import OS
from patchman.domains.models import Domain
from patchman.packages.models import Package, PackageName
from patchman.repos.models import Repository

class Report(models.Model):

    RPM = 'R'
    DEB = 'D'

    REPO_TYPES = (
        (RPM, 'rpm'),
        (DEB, 'deb'),
    )

    time = models.DateTimeField(auto_now_add=True)
    repotype = models.CharField(max_length=1, choices=REPO_TYPES, null=True)
    host = models.CharField(max_length=255, null=True)
    domain = models.CharField(max_length=255, null=True)
    tag = models.CharField(max_length=255, null=True)
    kernel = models.CharField(max_length=255, null=True)
    arch = models.CharField(max_length=255, null=True)
    os = models.CharField(max_length=255, null=True)
    report_ip = models.IPAddressField(null=True)
    version = models.CharField(max_length=255, null=True)
    useragent = models.CharField(max_length=255, null=True)
    processed = models.BooleanField(default=False)
    packages = models.TextField(null=True, blank=True)

    def __unicode__(self):
        host=self.host
        return '%s %s' % (self.time, host)

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

        if 'type' in data:
            if data['type'] == 'dpkg' or data['type'] == 'deb':
                self.repotype=Report.DEB
            if data['type'] == 'rpm':
                self.repotype=Report.RPM

        if 'tag' in data:
            self.tag=data['tag']
        else:
            self.tag=''

        if 'version' in data:
            self.version=data['version']
        else:
            self.version=''
# set defaults for all these elses

        if 'pkgs' in data:
            self.packages = data['pkgs']

        self.save()

