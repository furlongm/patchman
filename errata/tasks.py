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

from celery import shared_task

from security.tasks import update_cves, update_cwes
from util import get_setting_of_type
from errata.sources.distros.arch import update_arch_errata
from errata.sources.distros.alma import update_alma_errata
from errata.sources.distros.debian import update_debian_errata
from errata.sources.distros.centos import update_centos_errata
from errata.sources.distros.rocky import update_rocky_errata
from errata.sources.distros.ubuntu import update_ubuntu_errata


def update_errata():
    """ Update all distros errata
    """
    errata_os_updates = get_setting_of_type(
        setting_name='ERRATA_OS_UPDATES',
        setting_type=list,
        default=['rocky', 'alma', 'arch', 'ubuntu', 'debian', 'rhel', 'suse', 'amazon'],
    )
#    if 'arch' in errata_os_updates:
#        update_arch_errata()
#    if 'alma' in errata_os_updates:
#        update_alma_errata()
    if 'rocky' in errata_os_updates:
        update_rocky_errata()
    if 'debian' in errata_os_updates:
        update_debian_errata()
    if 'ubuntu' in errata_os_updates:
        update_ubuntu_errata()
    if 'rhel' in errata_os_updates:
        # update_rhel_errata()
        pass
    if 'suse' in errata_os_updates:
        # update_suse_errata()
        pass
    if 'amazon' in errata_os_updates:
        # update_amazon_errata()
        pass
    if 'centos' in errata_os_updates:
        update_centos_errata()


@shared_task
def update_errata_and_cves():
    """ Task to update all errata
    """
    update_errata.delay()
    update_cves.delay()
    update_cwes.delay()
