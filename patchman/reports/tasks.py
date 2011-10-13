import os
import sys
import string
import bz2
import gzip
import StringIO
import re
import hashlib
import datetime
import argparse
import math
from StringIO import StringIO
from lxml import etree
from debian.debian_support import Version
from debian.deb822 import Sources
from urllib2 import Request, urlopen

from django.db.utils import IntegrityError
from django.db import connection
from django.db.models import Q, Count
from django.dispatch import Signal

from patchman.hosts.models import Host
from patchman.operatingsystems.models import OS, OSGroup
from patchman.domains.models import Domain
from patchman.packages.models import Package, PackageName, PackageString, PackageUpdate
from patchman.repos.models import Repository, RepoPackage
from patchman.arch.models import PackageArchitecture, MachineArchitecture
from patchman.reports.models import Report

from patchman.hosts.signals import host_update_found

from celery.decorators import task


def process_packages(report, host):

    packages = []

    if report.packages:
        for i, p in enumerate(report.packages.splitlines()):
            packages.append(p.replace('\'','').split(' '))
        for i, pkg in enumerate(packages):
            if report.protocol == '1':
                if pkg[4] != '':
                    p_arch, c = PackageArchitecture.objects.get_or_create(name=pkg[4])
                else:
                    p_arch, c = PackageArchitecture.objects.get_or_create(name='unknown')
                p_name, c = PackageName.objects.get_or_create(name=pkg[0].lower())
                if pkg[1]:
                    p_epoch = pkg[1]
                    if p_epoch == '0':
                        p_epoch = ''
                else:
                    p_epoch = ''
                p_version = pkg[2]
                if pkg[3]:
                    p_release = pkg[3]
                else:
                    p_release = ''
                p_type = Package.UNKNOWN
                if pkg[5] == 'deb':
                    p_type = Package.DEB
                if pkg[5] == 'rpm':
                    p_type = Package.RPM
                package, c = Package.objects.get_or_create(name=p_name, arch=p_arch, epoch=p_epoch, version=p_version, release=p_release, packagetype=p_type)
                host.packages.add(package)
                del package
        host.save()

def create_or_update_host(report):

    if report.host and report.os and report.kernel and report.domain and report.arch:
        os, c = OS.objects.get_or_create(name=report.os)
        domain, c = Domain.objects.get_or_create(name=report.domain)
        arch, c = MachineArchitecture.objects.get_or_create(name=report.arch)
        host, c = Host.objects.get_or_create(
            hostname=report.host,
            defaults={
                'ipaddress':report.report_ip,
                'arch':arch,
                'os':os,
                'domain':domain,
                'lastreport':report.time
            }
        )
        host.ipaddress=report.report_ip
        host.kernel=report.kernel
        host.arch=arch
        host.os=os
        host.domain=domain
        host.lastreport=report.time
        host.tags=report.tags
# TODO: fix this to use stringpackage sets to remove/add
# or queryset sets
        host.packages.clear()
        host.save()
        process_packages(report, host)
        host.save()
        return True
    else:
        return False



@task()
def process_reports(report_host):
    report_hosts = []
    if report_host:
        try:
            report_hosts = Report.objects.filter(processed=False, host=report_host).order_by('time')
            message = 'Processing reports for host %s' % report_host
        except Report:
            message = 'No reports exist for host %s' % report_host
    else:
        message = 'Processing reports for all hosts'
        report_hosts = Report.objects.filter(processed=force).order_by('time')

    f = open('/tmp/samm', 'w')
    f.write("%s" % report_hosts)
    f.write("%s" % report_host)
    f.close()
    for report in report_hosts:
        if create_or_update_host(report):
            report.processed = True
            report.save()



def print_update(update, signal, *args, **kwargs):
    pass

@task()
def find_host_updates(update_host):

    update_hosts = []

    if update_host:
        try:
            update_hosts.append(Host.objects.get(hostname=update_host))
            message = 'Finding updates for host %s' % update_host
        except:
            message = 'Host %s does not exist' % update_host
    else:
        message = 'Finding updates for all hosts'
        update_hosts = Host.objects.all()


    for host in update_hosts:
        host_update_found.connect(print_update)
        host.find_updates()

@task()
def clean_updates():

    for update in PackageUpdate.objects.all():
        if update.host_set.all().count() == 0:
            update.delete()
        
