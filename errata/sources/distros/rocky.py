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
import concurrent.futures
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from django.db.utils import OperationalError

from operatingsystems.utils import get_or_create_osrelease
from packages.models import Package
from packages.utils import parse_package_string, get_or_create_package
from patchman.signals import pbar_start, pbar_update
from util import get_url, fetch_content, info_message, error_message


def update_rocky_errata(concurrent_processing=True):
    """ Update Rocky Linux errata
    """
    rocky_errata_api_host = 'https://apollo.build.resf.org'
    rocky_errata_api_url = '/api/v3/'
    if check_rocky_errata_endpoint_health(rocky_errata_api_host):
        advisories = fetch_rocky_advisories(rocky_errata_api_host, rocky_errata_api_url, concurrent_processing)
        process_rocky_errata(advisories, concurrent_processing)


def check_rocky_errata_endpoint_health(rocky_errata_api_host):
    """ Check Rocky Linux errata endpoint health
    """
    rocky_errata_healthcheck_path = '/_/healthz'
    rocky_errata_healthcheck_url = rocky_errata_api_host + rocky_errata_healthcheck_path
    headers = {'Accept': 'application/json'}
    res = get_url(rocky_errata_healthcheck_url, headers=headers)
    data = fetch_content(res, 'Rocky Linux Errata API healthcheck')
    try:
        health = json.loads(data)
        if health.get('status') == 'ok':
            s = f'Rocky Errata API healthcheck OK: {rocky_errata_healthcheck_url}'
            info_message.send(sender=None, text=s)
            return True
        else:
            s = f'Rocky Errata API healthcheck FAILED: {rocky_errata_healthcheck_url}'
            error_message.send(sender=None, text=s)
            return False
    except Exception as e:
        s = f'Rocky Errata API healthcheck exception occured: {rocky_errata_healthcheck_url}\n'
        s += str(e)
        error_message.send(sender=None, text=s)
        return False


def fetch_rocky_advisories(rocky_errata_api_host, rocky_errata_api_url, concurrent_processing):
    """ Fetch Rocky Linux advisories and return the list
    """
    if concurrent_processing:
        return fetch_rocky_advisories_concurrently(rocky_errata_api_host, rocky_errata_api_url)
    else:
        return fetch_rocky_advisories_serially(rocky_errata_api_host, rocky_errata_api_url)


def fetch_rocky_advisories_serially(rocky_errata_api_host, rocky_errata_api_url):
    """ Fetch Rocky Linux advisories serially and return the list
    """
    rocky_errata_advisories_url = rocky_errata_api_host + rocky_errata_api_url + 'advisories/'
    headers = {'Accept': 'application/json'}
    page = 1
    pages = None
    advisories = []
    params = {'page': 1, 'size': 100}
    while True:
        res = get_url(rocky_errata_advisories_url, headers=headers, params=params)
        data = fetch_content(res, f'Rocky Advisories {page}{"/"+pages if pages else ""}')
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


def fetch_rocky_advisories_concurrently(rocky_errata_api_host, rocky_errata_api_url):
    """ Fetch Rocky Linux advisories concurrently and return the list
    """
    rocky_errata_advisories_url = rocky_errata_api_host + rocky_errata_api_url + 'advisories/'
    headers = {'Accept': 'application/json'}
    advisories = []
    params = {'page': 1, 'size': 100}
    res = get_url(rocky_errata_advisories_url, headers=headers, params=params)
    data = fetch_content(res, 'Rocky Advisories Page 1')
    advisories_dict = json.loads(data)
    links = advisories_dict.get('links')
    last_link = links.get('last')
    pages = int(last_link.split('=')[-1])
    ptext = 'Fetching Rocky Advisories'
    pbar_start.send(sender=None, ptext=ptext, plen=pages)
    i = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(get_rocky_advisory, rocky_errata_advisories_url, page)
                   for page in range(1, pages + 1)]
        for future in concurrent.futures.as_completed(futures):
            advisories += future.result()
            i += 1
            pbar_update.send(sender=None, index=i + 1)
    return advisories


def get_rocky_advisory(rocky_errata_advisories_url, page):
    """ Fetch a single Rocky Linux advisory
    """
    headers = {'Accept': 'application/json'}
    params = {'page': page, 'size': 100}
    res = get_url(rocky_errata_advisories_url, headers=headers, params=params)
    data = res.content
    advisories_dict = json.loads(data)
    return advisories_dict.get('advisories')


def process_rocky_errata(advisories, concurrent_processing):
    """ Process Rocky Linux Errata
    """
    if concurrent_processing:
        process_rocky_errata_concurrently(advisories)
    else:
        process_rocky_errata_serially(advisories)


def process_rocky_errata_serially(advisories):
    """ Process Rocky Linux errata serially
    """
    elen = len(advisories)
    pbar_start.send(sender=None, ptext=f'Processing {elen} Rocky Errata', plen=elen)
    for i, advisory in enumerate(advisories):
        process_rocky_erratum(advisory)
        pbar_update.send(sender=None, index=i + 1)


def process_rocky_errata_concurrently(advisories):
    """ Process Rocky Linux errata concurrently
    """
    elen = len(advisories)
    pbar_start.send(sender=None, ptext=f'Processing {elen} Rocky Errata', plen=elen)
    i = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=25) as executor:
        futures = [executor.submit(process_rocky_erratum, advisory) for advisory in advisories]
        for future in concurrent.futures.as_completed(futures):
            i += 1
            pbar_update.send(sender=None, index=i + 1)


@retry(
    retry=retry_if_exception_type(OperationalError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=15),
)
def process_rocky_erratum(advisory):
    """ Process a single Rocky Linux erratum
    """
    from errata.utils import get_or_create_erratum
    try:
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
    except Exception as exc:
        error_message.send(sender=None, text=exc)


def add_rocky_erratum_references(e, advisory):
    """ Add Rocky Linux errata references
    """
    e.add_reference('Rocky Advisory', 'https://apollo.build.resf.org/{e.name}')
    e.add_reference('Rocky Advisory', 'https://errata.rockylinux.org/{e.name}')
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
    for affected_os in affected_oses:
        variant = affected_os.get('variant')
        major_version = affected_os.get('major_version')
        osrelease_name = f'{variant} {major_version}'
        osrelease = get_or_create_osrelease(name=osrelease_name)
        e.osreleases.add(osrelease)


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
                    arch,
                )
                for match in matching_modules:
                    match.packages.add(pkg)
