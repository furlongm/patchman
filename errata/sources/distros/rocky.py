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

from django.db import transaction

from arch.models import MachineArchitecture
from packages.models import Package
from packages.utils import parse_package_string, get_or_create_package
from util import get_url, download_url, info_message, error_message
from patchman.signals import progress_info_s, progress_update_s


def update_rocky_errata():
    """ Update Rocky Linux errata
    """
    rocky_errata_api_host = 'https://apollo.build.resf.org'
    rocky_errata_api_url = '/api/v3/'
    if check_rocky_errata_endpoint_health(rocky_errata_api_host):
        advisories = download_rocky_advisories(rocky_errata_api_host, rocky_errata_api_url)
        process_rocky_errata(advisories)


def check_rocky_errata_endpoint_health(rocky_errata_api_host):
    """ Check Rocky Linux errata endpoint health
    """
    rocky_errata_healthcheck_path = '/_/healthz'
    rocky_errata_healthcheck_url = rocky_errata_api_host + rocky_errata_healthcheck_path
    headers = {'Accept': 'application/json'}
    res = get_url(rocky_errata_healthcheck_url, headers=headers)
    data = download_url(res, 'Rocky Linux Errata API healthcheck')
    try:
        health = json.loads(data)
        if health.get('status') == 'ok':
            s = f'Rocky Linux Errata API healthcheck OK: {rocky_errata_healthcheck_url}'
            info_message.send(sender=None, text=s)
            return True
        else:
            s = f'Rocky Linux Errata API healthcheck FAILED: {rocky_errata_healthcheck_url}'
            error_message.send(sender=None, text=s)
            return False
    except Exception as e:
        s = f'Rocky Linux Errata API healthcheck exception occured: {rocky_errata_healthcheck_url}\n'
        s += str(e)
        error_message.send(sender=None, text=s)
        return False


def download_rocky_advisories(rocky_errata_api_host, rocky_errata_api_url):
    """ Download Rocky Linux advisories and return the list
    """
    rocky_errata_advisories_url = rocky_errata_api_host + rocky_errata_api_url + 'advisories/'
    headers = {'Accept': 'application/json'}
    page = 1
    pages = None
    advisories = []
    params = {'page': 1, 'size': 100}
    while True:
        res = get_url(rocky_errata_advisories_url, headers=headers, params=params)
        data = download_url(res, f'Rocky Linux Advisories {page}{"/"+pages if pages else ""}')
        advisories_dict = json.loads(data)
        advisories += advisories_dict.get('advisories')
        links = advisories_dict.get('links')
        if page == 1:
            last_link = links.get('last')
            pages = last_link.split('=')[-1]
        next_link = links.get('next')
        if next_link:
            rocky_errata_advisories_url = rocky_errata_api_host + next_link
            params = {}
            page += 1
        else:
            break
    return advisories


def process_rocky_errata(advisories):
    """ Process Rocky Linux errata
    """
    from errata.utils import get_or_create_erratum
    elen = len(advisories)
    ptext = f'Processing {elen} Errata:'
    progress_info_s.send(sender=None, ptext=ptext, plen=elen)
    for i, advisory in enumerate(advisories):
        progress_update_s.send(sender=None, index=i + 1)
        erratum_name = advisory.get('name')
        e_type = advisory.get('kind').lower().replace(' ', '')
        issue_date = advisory.get('published_at')
        synopsis = advisory.get('synopsis')
        e, created = get_or_create_erratum(
            name=erratum_name,
            e_type=e_type,
            issue_date=issue_date,
            synopsis=synopsis,
        )
        add_rocky_erratum_references(e, advisory)
        add_rocky_erratum_oses(e, advisory)
        add_rocky_erratum_packages(e, advisory)


def add_rocky_erratum_references(e, advisory):
    """ Add Rocky Linux errata references
    """
    advisory_cves = advisory.get('cves')
    for a_cve in advisory_cves:
        cve_id = a_cve.get('cve')
        e.add_cve(cve_id)
    fixes = advisory.get('fixes')
    for fix in fixes:
        url = fix.get('source')
        e.add_reference('Bug Report', url)


def add_rocky_erratum_oses(e, advisory):
    """ Update OS Variant, OS Release and MachineArch for Rocky Linux errata
    """
    affected_oses = advisory.get('affected_products')
    from operatingsystems.models import OSVariant, OSRelease
    for affected_os in affected_oses:
        arch = affected_os.get('arch')
        variant = affected_os.get('variant')
        major_version = affected_os.get('major_version')
        osrelease_name = f'{variant} {major_version}'
        with transaction.atomic():
            osrelease, created = OSRelease.objects.get_or_create(name=osrelease_name)
        osvariant_name = affected_os.get('name').replace(' (Legacy)', '')
        with transaction.atomic():
            m_arch, created = MachineArchitecture.objects.get_or_create(name=arch)
        with transaction.atomic():
            osvariant, created = OSVariant.objects.get_or_create(name=osvariant_name, arch=m_arch)
        osvariant.osrelease = osrelease
        osvariant.save()
        e.osreleases.add(osrelease)
    e.save()


def add_rocky_erratum_packages(e, advisory):
    """ Parse and add packages for Rocky Linux errata
    """
    from modules.utils import get_matching_modules
    packages = advisory.get('packages')
    for package in packages:
        package_name = package.get('nevra')
        if package_name:
            name, epoch, ver, rel, dist, arch = parse_package_string(package_name)
            p_type = Package.RPM
            pkg = get_or_create_package(name, epoch, ver, rel, arch, p_type)
            e.packages.add(pkg)
            module_name = package.get('module_name')
            module_context = package.get('module_context')
            module_stream = package.get('module_stream')
            module_version = package.get('module_version')
            if module_name and module_context and module_stream and module_version:
                matching_modules = get_matching_modules(
                    module_name,
                    module_stream,
                    module_version,
                    module_context,
                    arch)
                for match in matching_modules:
                    match.packages.add(pkg)
    e.save()
