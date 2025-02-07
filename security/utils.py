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

from security.models import CVE, CWE


def get_cve_reference(cve_id):
    """ Given a CVE ID, return a dictionary with the URL to the CVE record.
    """
    url = f'https://www.cve.org/CVERecord?id={cve_id}'
    return {'er_type': 'CVE', 'url': url}


def get_or_create_cve(cve_id):
    """ Given a CVE ID, get or create a CVE object.
    """
    cve, created = CVE.objects.get_or_create(cve_id=cve_id)
    return cve


def update_cves():
    """ Download the latest CVE data from the CVE API.
        e.g. https://cveawg.mitre.org/api/cve/CVE-2024-1234
    """
    for cve in CVE.objects.all():
        cve.download_cve_data()


def update_cwes():
    """ Download the latest CWEs from the CWE API.
        e.g. https://cwe-api.mitre.org/api/v1/cwe/74,79
             https://cwe-api.mitre.org/api/v1/cwe/weakness/79
    """
    for cwe in CWE.objects.all():
        cwe.download_cwe_data()
