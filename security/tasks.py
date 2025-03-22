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

from security.models import CVE, CWE


@shared_task
def update_cve(cve_id):
    """ Task to update a CVE
    """
    cve = CVE.objects.get(id=cve_id)
    cve.fetch_cve_data()


@shared_task
def update_cves():
    """ Task to update all CVEs
    """
    for cve in CVE.objects.all():
        update_cve.delay(cve.id)


@shared_task
def update_cwe(cwe_id):
    """ Task to update a CWE
    """
    cwe = CWE.objects.get(id=cwe_id)
    cwe.fetch_cwe_data()


@shared_task
def update_cwes():
    """ Task to update all CWEa
    """
    for cwe in CWE.objects.all():
        update_cwe.delay(cwe.id)
