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

from hosts.models import Host
from util.tables import BaseTable

CHECKBOX_TEMPLATE = '<input type="checkbox" name="selected_ids" value="{{ record.id }}" class="bulk-checkbox">'
SELECT_ALL_CHECKBOX = '<input type="checkbox" id="select-all-page" title="Select all on this page">'
HOSTNAME_TEMPLATE = '<a href="{{ record.get_absolute_url }}">{{ record.hostname }}</a>'
SEC_UPDATES_TEMPLATE = (
    '{% with count=record.get_num_security_updates %}'
    '{% if count != 0 %}<span style="color:red">{{ count }}</span>{% else %}{% endif %}'
    '{% endwith %}'
)
BUG_UPDATES_TEMPLATE = (
    '{% with count=record.get_num_bugfix_updates %}'
    '{% if count != 0 %}<span style="color:orange">{{ count }}</span>{% else %}{% endif %}'
    '{% endwith %}'
)
AFFECTED_ERRATA_TEMPLATE = (
    '{% with count=record.errata.count %}'
    '{% if count != 0 %}'
    '<a href="{% url \'errata:erratum_list\' %}?host={{ record.hostname }}">{{ count }}</a>'
    '{% else %}{% endif %}{% endwith %}'
)
OSVARIANT_TEMPLATE = (
    '{% if record.osvariant %}'
    '<a href="{{ record.osvariant.get_absolute_url }}">{{ record.osvariant }}</a>'
    '{% endif %}'
)
PACKAGES_TEMPLATE = (
    '<a href="{% url \'packages:package_list\' %}?host={{ record.hostname }}">'
    '{{ record.packages_count }}</a>'
)
LASTREPORT_TEMPLATE = (
    '{% load report_alert %}'
    '{{ record.lastreport }} {% report_alert record.lastreport %}'
)
REBOOT_TEMPLATE = '{% load common %}{% no_yes_img record.reboot_required %}'


class HostTable(BaseTable):
    selection = tables.TemplateColumn(
        CHECKBOX_TEMPLATE,
        orderable=False,
        verbose_name=SELECT_ALL_CHECKBOX,
        attrs={'th': {'class': 'min-width-col centered'}, 'td': {'class': 'min-width-col centered'}},
    )
    hostname = tables.TemplateColumn(
        HOSTNAME_TEMPLATE,
        order_by='hostname',
        verbose_name='Hostname',
        attrs={'th': {'class': 'col-sm-3'}, 'td': {'class': 'col-sm-3'}},
    )
    sec_updates = tables.TemplateColumn(
        SEC_UPDATES_TEMPLATE,
        order_by='sec_updates_count',
        verbose_name='Security Updates',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    bug_updates = tables.TemplateColumn(
        BUG_UPDATES_TEMPLATE,
        order_by='bug_updates_count',
        verbose_name='Bugfix Updates',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    affected_errata = tables.TemplateColumn(
        AFFECTED_ERRATA_TEMPLATE,
        order_by='errata_count',
        verbose_name='Affected by Errata',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    kernel = tables.Column(
        verbose_name='Running Kernel',
        attrs={'th': {'class': 'col-sm-2'}, 'td': {'class': 'col-sm-2'}},
    )
    osvariant = tables.TemplateColumn(
        OSVARIANT_TEMPLATE,
        order_by='osvariant__name',
        verbose_name='OS Variant',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    packages_installed = tables.TemplateColumn(
        PACKAGES_TEMPLATE,
        order_by='packages_count',
        verbose_name='Packages',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )
    lastreport = tables.TemplateColumn(
        LASTREPORT_TEMPLATE,
        order_by='lastreport',
        verbose_name='Last Report',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1'}},
    )
    reboot_required = tables.TemplateColumn(
        REBOOT_TEMPLATE,
        order_by='reboot_required',
        verbose_name='Reboot Status',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'col-sm-1 centered'}},
    )

    class Meta(BaseTable.Meta):
        model = Host
        fields = (
            'selection', 'hostname', 'packages_installed', 'sec_updates', 'bug_updates',
            'affected_errata', 'kernel', 'osvariant', 'lastreport', 'reboot_required',
        )
