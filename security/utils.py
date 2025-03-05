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

from urllib.parse import urlparse

from security.models import CVE, CWE, Reference


def get_cve_reference(cve_id):
    """ Given a CVE ID, return a dictionary with the URL to the CVE record.
    """
    url = f'https://www.cve.org/CVERecord?id={cve_id}'
    return {'ref_type': 'CVE', 'url': url}


def get_or_create_cve(cve_id):
    """ Given a CVE ID, get or create a CVE object.
    """
    cve, created = CVE.objects.get_or_create(cve_id=cve_id)
    return cve


def update_cves(cve_id=None, download_nist_data=False):
    """ Download the latest CVE data from the CVE API.
        e.g. https://cveawg.mitre.org/api/cve/CVE-2024-1234
    """
    if cve_id:
        cve = CVE.objects.get(cve_id=cve_id)
        cve.download_cve_data(download_nist_data, sleep_secs=0)
    else:
        for cve in CVE.objects.all():
            cve.download_cve_data(download_nist_data)


def update_cwes(cve_id=None):
    """ Download the latest CWEs from the CWE API.
        e.g. https://cwe-api.mitre.org/api/v1/cwe/74,79
             https://cwe-api.mitre.org/api/v1/cwe/weakness/79
    """
    if cve_id:
        cve = CVE.objects.get(cve_id=cve_id)
        cwes = cve.cwes.all()
    else:
        cwes = CWE.objects.all()
    for cwe in cwes:
        cwe.download_cwe_data()


def fixup_reference(ref):
    """ Fix up a Security Reference object to normalize the URL and type
    """
    url = urlparse(ref.get('url'))
    ref_type = ref.get('ref_type')
    if 'lists' in url.hostname or 'lists' in url.path:
        ref_type = 'Mailing List'
    if ref_type == 'bugzilla' or 'bug' in url.hostname or 'bugs' in url.path:
        ref_type = 'Bug Tracker'
    if ('ubuntu.com' in url.hostname and 'usn/' in url.path) or url.hostname == 'usn.ubuntu.com':
        netloc = url.netloc.replace('usn.', '').replace('www.', '')
        path = url.path.replace('usn/', 'security/notices/').replace('usn', 'USN').rstrip('/')
        usn_id = path.split('/')[-1]
        if 'USN' not in usn_id:
            path = '/'.join(path.split('/')[:-1]) + '/USN-' + usn_id
        url = url._replace(netloc=netloc, path=path)
    if url.hostname == 'ubuntu.com' and url.path.startswith('/security/notices/USN'):
        ref_type = 'USN'
    if 'launchpad.net' in url.hostname:
        ref_type = 'Bug Tracker'
        netloc = url.netloc.replace('bugs.', '')
        bug = url.path.split('/')[-1]
        path = f'/bugs/{bug}'
        url = url._replace(netloc=netloc, path=path)
    if url.hostname in ['bugzilla.redhat.com', 'bugzilla.opensuse.org', 'bugs.suse.com'] and \
            url.path == '/show_bug.cgi':
        bug = url.query.split('=')[1]
        path = f'/{bug}'
        url = url._replace(path=path, query='')
    if url.hostname == 'rhn.redhat.com':
        netloc = url.netloc.replace('rhn', 'access')
        path = url.path.replace('.html', '')
        url = url._replace(netloc=netloc, path=path)
    if url.hostname == 'access.redhat.com':
        if 'l1d-cache-eviction-and-vector-register-sampling' in url.path or \
                'security/vulnerabilities/speculativeexecution' in url.path or \
                'security/vulnerabilities/stackguard' in url.path:
            ref_type = 'Link'
        elif 'security/cve' in url.path:
            return
        else:
            old_ref = url.path.split('/')[-1]
            refs = old_ref.split('-')
            if ':' not in url.path:
                try:
                    new_ref = f'{refs[0]}-{refs[1]}:{refs[2]}'
                    path = url.path.replace(old_ref, new_ref)
                    url = url._replace(path=path)
                except IndexError:
                    pass
            ref_type = refs[0].upper()
    final_url = url.geturl()
    if final_url in ['https://launchpad.net/bugs/', 'https://launchpad.net/bugs/XXXXXX']:
        return
    ref['ref_type'] = ref_type
    ref['url'] = final_url
    return ref


def get_or_create_reference(ref_type, url):
    """ Get or create a Reference object.
    """
    reference = fixup_reference({'ref_type': ref_type, 'url': url})
    if reference:
        ref, created = Reference.objects.get_or_create(
            ref_type=reference.get('ref_type'),
            url=reference.get('url'),
        )
        return ref
