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

from repos.models import Mirror, Repository
from util.tables import BaseTable

# RepositoryTable templates
CHECKBOX_TEMPLATE = '<input type="checkbox" name="selected_ids" value="{{ record.id }}" class="bulk-checkbox">'
SELECT_ALL_CHECKBOX = '<input type="checkbox" id="select-all-page" title="Select all on this page">'
REPO_NAME_TEMPLATE = '<a href="{{ record.get_absolute_url }}">{{ record }}</a>'
MIRRORS_TEMPLATE = (
    '<a href="{% url \'repos:mirror_list\' %}?repo_id={{ record.id }}">'
    '{{ record.mirror_set.count }}</a>'
)
REPO_ENABLED_TEMPLATE = '{% load common %}{% yes_no_img record.enabled %}'
SECURITY_TEMPLATE = '{% load common %}{% yes_no_img record.security %}'
AUTH_REQUIRED_TEMPLATE = '{% if record.auth_required %}Yes{% else %}No{% endif %}'

# MirrorTable templates
MIRROR_CHECKBOX_TEMPLATE = '<input type="checkbox" name="selected_ids" value="{{ record.id }}" class="bulk-checkbox">'
MIRROR_ID_TEMPLATE = '<a href="{{ record.get_absolute_url }}">{{ record.id }}</a>'
MIRROR_URL_TEMPLATE = '<a href="{{ record.url }}" class="truncate-url">{{ record.url }}</a>'
MIRROR_PACKAGES_TEMPLATE = (
    '{% if not record.mirrorlist %}'
    '<a href="{% url \'packages:package_list\' %}?mirror_id={{ record.id }}">'
    '{{ record.packages.count }}</a>{% endif %}'
)
MIRROR_ENABLED_TEMPLATE = '{% load common %}{% yes_no_img record.enabled %}'
REFRESH_TEMPLATE = '{% load common %}{% yes_no_img record.refresh %}'
MIRRORLIST_TEMPLATE = '{% load common %}{% yes_no_img record.mirrorlist %}'
LAST_ACCESS_OK_TEMPLATE = '{% load common %}{% yes_no_img record.last_access_ok %}'
CHECKSUM_TEMPLATE = '{% if not record.mirrorlist %}{{ record.packages_checksum|truncatechars:16 }}{% endif %}'


class RepositoryTable(BaseTable):
    selection = tables.TemplateColumn(
        CHECKBOX_TEMPLATE,
        orderable=False,
        verbose_name=SELECT_ALL_CHECKBOX,
        attrs={'th': {'class': 'min-width-col centered'}, 'td': {'class': 'min-width-col centered'}},
    )
    repo_name = tables.TemplateColumn(
        REPO_NAME_TEMPLATE,
        order_by='name',
        verbose_name='Repo Name',
        attrs={'th': {'class': 'col-sm-4'}, 'td': {'class': 'col-sm-4'}},
    )
    repo_id = tables.Column(
        verbose_name='Repo ID',
        default='',
        attrs={'th': {'class': 'col-sm-3'}, 'td': {'class': 'col-sm-3'}},
    )
    mirrors = tables.TemplateColumn(
        MIRRORS_TEMPLATE,
        orderable=False,
        verbose_name='Mirrors',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    repo_enabled = tables.TemplateColumn(
        REPO_ENABLED_TEMPLATE,
        orderable=False,
        verbose_name='Enabled',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    security = tables.TemplateColumn(
        SECURITY_TEMPLATE,
        orderable=False,
        verbose_name='Security',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    auth_required = tables.TemplateColumn(
        AUTH_REQUIRED_TEMPLATE,
        orderable=False,
        verbose_name='Auth Required',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )

    class Meta(BaseTable.Meta):
        model = Repository
        fields = (
            'selection', 'repo_name', 'repo_id', 'mirrors',
            'repo_enabled', 'security', 'auth_required',
        )


class MirrorTable(BaseTable):
    selection = tables.TemplateColumn(
        MIRROR_CHECKBOX_TEMPLATE,
        orderable=False,
        verbose_name=SELECT_ALL_CHECKBOX,
        attrs={'th': {'class': 'min-width-col centered'}, 'td': {'class': 'min-width-col centered'}},
    )
    mirror_id = tables.TemplateColumn(
        MIRROR_ID_TEMPLATE,
        order_by='id',
        verbose_name='ID',
        attrs={'th': {'class': 'min-width-col'}, 'td': {'class': 'min-width-col'}},
    )
    mirror_url = tables.TemplateColumn(
        MIRROR_URL_TEMPLATE,
        orderable=False,
        verbose_name='URL',
        attrs={'th': {'class': 'col-sm-2'}, 'td': {'class': 'col-sm-2 truncate-cell'}},
    )
    mirror_packages = tables.TemplateColumn(
        MIRROR_PACKAGES_TEMPLATE,
        order_by='packages_count',
        verbose_name='Packages',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    mirror_enabled = tables.TemplateColumn(
        MIRROR_ENABLED_TEMPLATE,
        orderable=False,
        verbose_name='Enabled',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    refresh = tables.TemplateColumn(
        REFRESH_TEMPLATE,
        orderable=False,
        verbose_name='Refresh',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    mirrorlist = tables.TemplateColumn(
        MIRRORLIST_TEMPLATE,
        orderable=False,
        verbose_name='Mirrorlist/Metalink',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    last_access_ok = tables.TemplateColumn(
        LAST_ACCESS_OK_TEMPLATE,
        orderable=False,
        verbose_name='Last Access OK',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    timestamp = tables.Column(
        order_by='timestamp',
        verbose_name='Timestamp',
        attrs={'th': {'class': 'col-sm-2'}, 'td': {'class': 'col-sm-2'}},
    )
    checksum = tables.TemplateColumn(
        CHECKSUM_TEMPLATE,
        order_by='packages_checksum',
        verbose_name='Checksum',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )

    class Meta(BaseTable.Meta):
        model = Mirror
        fields = (
            'selection', 'mirror_id', 'mirror_url', 'mirror_packages', 'mirror_enabled', 'refresh',
            'mirrorlist', 'last_access_ok', 'timestamp', 'checksum',
        )
