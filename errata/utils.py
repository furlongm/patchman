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

from django.conf import settings
from django.db import transaction

from util import tz_aware_datetime, has_setting_of_type
from errata.models import Erratum
from errata.sources.distros.arch import update_arch_errata
from errata.sources.distros.alma import update_alma_errata
from errata.sources.distros.debian import update_debian_errata
from errata.sources.distros.centos import update_centos_errata
from errata.sources.distros.rocky import update_rocky_errata
from errata.sources.distros.ubuntu import update_ubuntu_errata
from patchman.signals import progress_info_s, progress_update_s


def update_errata():
    """ Update all distros errata
    """
    if has_setting_of_type('ERRATA_OS_UPDATES', list):
        errata_os_updates = settings.ERRATA_OS_UPDATES
    else:
        errata_os_updates = ['rocky', 'alma', 'arch', 'ubuntu', 'debian', 'rhel', 'suse', 'amazon']
    if 'arch' in errata_os_updates:
        update_arch_errata()
    if 'alma' in errata_os_updates:
        update_alma_errata()
    if 'rocky' in errata_os_updates:
        update_rocky_errata()
    if 'debian' in errata_os_updates:
        update_debian_errata()
    if 'ubuntu' in errata_os_updates:
        update_ubuntu_errata()
    if 'centos' in errata_os_updates:
        update_centos_errata()


def get_or_create_erratum(name, e_type, issue_date, synopsis):
    """ Get or create an Erratum object. Returns the object and created
    """
    with transaction.atomic():
        e, created = Erratum.objects.get_or_create(
            name=name,
            e_type=e_type,
            issue_date=tz_aware_datetime(issue_date),
            synopsis=synopsis,
        )
    return e, created


def fixup_erratum_reference(eref):
    """ Fix up an ErratumReference object to normalize the URL and type
    """
    url = urlparse(eref.get('url'))
    er_type = eref.get('er_type')
    if 'lists' in url.hostname or 'lists' in url.path:
        er_type = 'Mailing List'
    if er_type == 'bugzilla' or 'bug' in url.hostname or 'bugs' in url.path:
        er_type = 'Bug Tracker'
    if ('ubuntu.com' in url.hostname and 'usn/' in url.path) or url.hostname == 'usn.ubuntu.com':
        netloc = url.netloc.replace('usn.', '').replace('www.', '')
        path = url.path.replace('usn/', 'security/notices/').replace('usn', 'USN').rstrip('/')
        usn_id = path.split('/')[-1]
        if 'USN' not in usn_id:
            path = '/'.join(path.split('/')[:-1]) + '/USN-' + usn_id
        url = url._replace(netloc=netloc, path=path)
    if url.hostname == 'ubuntu.com' and url.path.startswith('/security/notices/USN'):
        er_type = 'USN'
    if 'launchpad.net' in url.hostname:
        er_type = 'Bug Tracker'
        netloc = url.netloc.replace('bugs.', '')
        bug = url.path.split('/')[-1]
        path = f'/bugs/{bug}'
        url = url._replace(netloc=netloc, path=path)
    if url.hostname == 'bugzilla.redhat.com' and url.path == '/show_bug.cgi':
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
            er_type = 'Link'
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
            er_type = refs[0].upper()
    final_url = url.geturl()
    if final_url in ['https://launchpad.net/bugs/', 'https://launchpad.net/bugs/XXXXXX']:
        return
    eref['er_type'] = er_type
    eref['url'] = final_url
    return eref


def mark_errata_security_updates():
    """ For each set of erratum packages, modify any PackageUpdate that
        should be marked as a security update.
    """
    elen = Erratum.objects.count()
    ptext = f'Scanning {elen} Errata:'
    progress_info_s.send(sender=None, ptext=ptext, plen=elen)
    for i, e in enumerate(Erratum.objects.all()):
        progress_update_s.send(sender=None, index=i + 1)
        e.scan_for_security_updates()
