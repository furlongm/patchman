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

from packages.models import Package, PackageName, PackageUpdate
from util.tables import BaseTable

PACKAGE_NAME_TEMPLATE = '<a href="{{ record.get_absolute_url }}">{{ record }}</a>'
PACKAGE_REPOS_TEMPLATE = (
    '<a href="{% url \'repos:repo_list\' %}?package_id={{ record.id }}">'
    'Available from {{ record.repo_count }} Repositories</a>'
)
PACKAGE_HOSTS_TEMPLATE = (
    '<a href="{% url \'hosts:host_list\' %}?package_id={{ record.id }}">'
    'Installed on {{ record.host_count }} Hosts</a>'
)
AFFECTED_TEMPLATE = (
    '<a href="{% url \'errata:erratum_list\' %}?package_id={{ record.id }}&type=affected">'
    'Affected by {{ record.affected_count }} Errata</a>'
)
FIXED_TEMPLATE = (
    '<a href="{% url \'errata:erratum_list\' %}?package_id={{ record.id }}&type=fixed">'
    'Provides fix in {{ record.fixed_count }} Errata</a>'
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
        order_by='repo_count',
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    package_hosts = tables.TemplateColumn(
        PACKAGE_HOSTS_TEMPLATE,
        verbose_name='Hosts',
        order_by='host_count',
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    affected = tables.TemplateColumn(
        AFFECTED_TEMPLATE,
        verbose_name='Affected',
        order_by='affected_count',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    fixed = tables.TemplateColumn(
        FIXED_TEMPLATE,
        verbose_name='Fixed',
        order_by='fixed_count',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )

    class Meta(BaseTable.Meta):
        model = Package
        fields = (
            'package_name', 'epoch', 'package_version', 'release', 'package_arch',
            'packagetype', 'package_repos', 'package_hosts', 'affected', 'fixed',
        )


PACKAGE_NAME_HOSTS_TEMPLATE = (
    '<a href="{% url \'hosts:host_list\' %}?package={{ record.name }}">'
    '{{ record.host_count }}</a>'
)


class PackageNameTable(BaseTable):
    packagename_name = tables.TemplateColumn(
        PACKAGE_NAME_TEMPLATE,
        order_by='name',
        verbose_name='Package',
        attrs={'th': {'class': 'col-sm-5'}, 'td': {'class': 'col-sm-5'}},
    )
    versions = tables.TemplateColumn(
        '{{ record.package_set.count }}',
        orderable=False,
        verbose_name='Versions',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    hosts = tables.TemplateColumn(
        PACKAGE_NAME_HOSTS_TEMPLATE,
        verbose_name='Hosts',
        order_by='host_count',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )

    class Meta(BaseTable.Meta):
        model = PackageName
        fields = ('packagename_name', 'versions', 'hosts')


UPDATE_OLD_TEMPLATE = (
    '<a href="{% url \'packages:package_detail\' record.oldpackage.id %}">'
    '{{ record.oldpackage }}</a>'
)
UPDATE_NEW_TEMPLATE = (
    '<a href="{% url \'packages:package_detail\' record.newpackage.id %}">'
    '{{ record.newpackage }}</a>'
)
UPDATE_HOSTS_TEMPLATE = (
    '<a href="{% url \'hosts:host_list\' %}?update_id={{ record.id }}">'
    '{{ record.host_count }}</a>'
)
UPDATE_AFFECTED_TEMPLATE = (
    '<a href="{% url \'errata:erratum_list\' %}?package_id={{ record.oldpackage.id }}&type=affected">'
    '{{ record.affected_count }}</a>'
)
UPDATE_FIXED_TEMPLATE = (
    '<a href="{% url \'errata:erratum_list\' %}?package_id={{ record.newpackage.id }}&type=fixed">'
    '{{ record.fixed_count }}</a>'
)


UPDATE_TYPE_TEMPLATE = (
    '{% if record.security %}'
    '<span class="label label-danger">Security</span>'
    '{% else %}'
    '<span class="label label-info">Bugfix</span>'
    '{% endif %}'
)


class PackageUpdateTable(BaseTable):
    oldpackage = tables.TemplateColumn(
        UPDATE_OLD_TEMPLATE,
        verbose_name='Installed',
        attrs={'th': {'class': 'col-sm-3'}, 'td': {'class': 'col-sm-3'}},
    )
    newpackage = tables.TemplateColumn(
        UPDATE_NEW_TEMPLATE,
        verbose_name='Available',
        attrs={'th': {'class': 'col-sm-3'}, 'td': {'class': 'col-sm-3'}},
    )
    security = tables.TemplateColumn(
        UPDATE_TYPE_TEMPLATE,
        verbose_name='Type',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    hosts = tables.TemplateColumn(
        UPDATE_HOSTS_TEMPLATE,
        verbose_name='Hosts',
        order_by='host_count',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    affected = tables.TemplateColumn(
        UPDATE_AFFECTED_TEMPLATE,
        verbose_name='Affected by Errata',
        order_by='affected_count',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    fixed = tables.TemplateColumn(
        UPDATE_FIXED_TEMPLATE,
        verbose_name='Fixed in Errata',
        order_by='fixed_count',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )

    class Meta(BaseTable.Meta):
        model = PackageUpdate
        fields = ('oldpackage', 'newpackage', 'security', 'hosts', 'affected', 'fixed')
