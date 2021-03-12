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

from django.db import models, IntegrityError, DatabaseError, transaction
from django.urls import reverse

from hosts.models import Host
from arch.models import MachineArchitecture
from operatingsystems.models import OS
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
    report_ip = models.GenericIPAddressField(null=True)
    protocol = models.CharField(max_length=255, null=True)
    useragent = models.CharField(max_length=255, null=True)
    processed = models.BooleanField(default=False)
    packages = models.TextField(null=True, blank=True)
    sec_updates = models.TextField(null=True, blank=True)
    bug_updates = models.TextField(null=True, blank=True)
    repos = models.TextField(null=True, blank=True)
    reboot = models.TextField(null=True, blank=True)

    class Meta(object):
        verbose_name_plural = 'Report'
        verbose_name_plural = 'Reports'
        ordering = ('-created',)

    def __str__(self):
        return '{0!s} {1!s}'.format(self.host, self.created.strftime('%c'))

    def get_absolute_url(self):
        return reverse('reports:report_detail', args=[str(self.id)])

    def parse(self, data, meta):

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

        attrs = ['arch', 'host', 'os', 'kernel', 'protocol', 'packages',
                 'tags', 'sec_updates', 'bug_updates', 'repos', 'reboot']

        for attr in attrs:
            setattr(self, attr, data.get(attr).strip())

        if self.host is not None:
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

            oses = OS.objects.all()
            with transaction.atomic():
                os, c = oses.get_or_create(name=self.os)

            machine_arches = MachineArchitecture.objects.all()
            with transaction.atomic():
                arch, c = machine_arches.get_or_create(name=self.arch)

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

            hosts = Host.objects.all()
            with transaction.atomic():
                host, c = hosts.get_or_create(
                    hostname=self.host,
                    defaults={
                        'ipaddress': self.report_ip,
                        'arch': arch,
                        'os': os,
                        'domain': domain,
                        'lastreport': self.created,
                    })

            host.ipaddress = self.report_ip
            host.kernel = self.kernel
            host.arch = arch
            host.os = os
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
                text = 'Processing report '
                text += '{0!s} - {1!s}'.format(self.id, self.host)
                info_message.send(sender=None, text=text)

            from reports.utils import process_packages, \
                process_repos, process_updates
            with transaction.atomic():
                process_repos(report=self, host=host)
            with transaction.atomic():
                process_packages(report=self, host=host)
            with transaction.atomic():
                process_updates(report=self, host=host)

            self.processed = True
            with transaction.atomic():
                self.save()

            if find_updates:
                if verbose:
                    text = 'Finding updates for report '
                    text += '{0!s} - {1!s}'.format(self.id, self.host)
                    info_message.send(sender=None, text=text)
                host.find_updates()
        else:
            if self.processed:
                text = 'Report {0!s} '.format(self.id)
                text += 'has already been processed'
                info_message.send(sender=None, text=text)
            else:
                text = 'Error: OS, kernel or arch not sent '
                text += 'with report {0!s}'.format(self.id)
                error_message.send(sender=None, text=text)
