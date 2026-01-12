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

from modules.models import Module
from util.tables import BaseTable

MODULE_NAME_TEMPLATE = '<a href="{{ record.get_absolute_url }}">{{ record.name }}</a>'
REPO_TEMPLATE = '<a href="{{ record.repo.get_absolute_url }}">{{ record.repo }}</a>'
PACKAGES_TEMPLATE = (
    '<a href="{% url \'packages:package_list\' %}?module_id={{ record.id }}">'
    '{{ record.packages.count }}</a>'
)


class ModuleTable(BaseTable):
    module_name = tables.TemplateColumn(
        MODULE_NAME_TEMPLATE,
        order_by='name',
        verbose_name='Name',
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    stream = tables.Column(
        verbose_name='Stream',
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    module_version = tables.Column(
        accessor='version',
        verbose_name='Version',
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    context = tables.Column(
        verbose_name='Context',
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    repo = tables.TemplateColumn(
        REPO_TEMPLATE,
        verbose_name='Repo',
        orderable=False,
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    module_packages = tables.TemplateColumn(
        PACKAGES_TEMPLATE,
        verbose_name='Packages',
        orderable=False,
        attrs={'th': {'class': 'col-sm-auto'}, 'td': {'class': 'col-sm-auto'}},
    )
    enabled_on_hosts = tables.TemplateColumn(
        '{{ record.host_set.count }}',
        verbose_name='Enabled on Hosts',
        orderable=False,
        attrs={'th': {'class': 'col-md-auto'}, 'td': {'class': 'col-md-auto'}},
    )

    class Meta(BaseTable.Meta):
        model = Module
        fields = (
            'module_name', 'stream', 'module_version', 'context',
            'repo', 'module_packages', 'enabled_on_hosts',
        )
