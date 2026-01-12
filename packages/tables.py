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

import django_tables2 as tables

from packages.models import Package, PackageName
from util.tables import BaseTable

PACKAGE_NAME_TEMPLATE = '<a href="{{ record.get_absolute_url }}">{{ record }}</a>'
PACKAGE_REPOS_TEMPLATE = (
    '<a href="{% url \'repos:repo_list\' %}?package_id={{ record.id }}">'
    'Available from {{ record.repo_count }} Repositories</a>'
)
PACKAGE_HOSTS_TEMPLATE = (
    '<a href="{% url \'hosts:host_list\' %}?package_id={{ record.id }}">'
    'Installed on {{ record.host_set.count }} Hosts</a>'
)
AFFECTED_TEMPLATE = (
    '<a href="{% url \'errata:erratum_list\' %}?package_id={{ record.id }}&type=affected">'
    'Affected by {{ record.affected_by_erratum.count }} Errata</a>'
)
FIXED_TEMPLATE = (
    '<a href="{% url \'errata:erratum_list\' %}?package_id={{ record.id }}&type=fixed">'
    'Provides fix in {{ record.provides_fix_in_erratum.count }} Errata</a>'
)


class PackageTable(BaseTable):
    package_name = tables.TemplateColumn(
        PACKAGE_NAME_TEMPLATE,
        order_by='name__name',
        verbose_name='Package',
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    epoch = tables.Column(
        verbose_name='Epoch',
        default='',
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    package_version = tables.Column(
        accessor='version',
        verbose_name='Version',
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    release = tables.Column(
        verbose_name='Release',
        default='',
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    package_arch = tables.Column(
        accessor='arch__name',
        verbose_name='Arch',
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    packagetype = tables.Column(
        accessor='packagetype',
        verbose_name='Type',
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    package_repos = tables.TemplateColumn(
        PACKAGE_REPOS_TEMPLATE,
        verbose_name='Repositories',
        orderable=False,
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    package_hosts = tables.TemplateColumn(
        PACKAGE_HOSTS_TEMPLATE,
        verbose_name='Hosts',
        orderable=False,
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    affected = tables.TemplateColumn(
        AFFECTED_TEMPLATE,
        verbose_name='Affected',
        orderable=False,
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    fixed = tables.TemplateColumn(
        FIXED_TEMPLATE,
        verbose_name='Fixed',
        orderable=False,
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )

    class Meta(BaseTable.Meta):
        model = Package
        fields = (
            'package_name', 'epoch', 'package_version', 'release', 'package_arch',
            'packagetype', 'package_repos', 'package_hosts', 'affected', 'fixed',
        )


class PackageNameTable(BaseTable):
    packagename_name = tables.TemplateColumn(
        PACKAGE_NAME_TEMPLATE,
        order_by='name',
        verbose_name='Package',
        attrs={'th': {'class': 'col-sm-6'}, 'td': {'class': 'col-sm-6'}},
    )
    versions = tables.TemplateColumn(
        '{{ record.package_set.count }}',
        orderable=False,
        verbose_name='Versions available',
        attrs={'th': {'class': 'col-sm-6'}, 'td': {'class': 'col-sm-6'}},
    )

    class Meta(BaseTable.Meta):
        model = PackageName
        fields = ('packagename_name', 'versions')
