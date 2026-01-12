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

from reports.models import Report
from util.tables import BaseTable

CHECKBOX_TEMPLATE = '<input type="checkbox" name="selected_ids" value="{{ record.id }}" class="bulk-checkbox">'
SELECT_ALL_CHECKBOX = '<input type="checkbox" id="select-all-page" title="Select all on this page">'
REPORT_ID_TEMPLATE = '<a href="{{ record.get_absolute_url }}">{{ record.id }}</a>'
PROCESSED_TEMPLATE = '{% load common %}{% yes_no_img record.processed %}'


class ReportTable(BaseTable):
    selection = tables.TemplateColumn(
        CHECKBOX_TEMPLATE,
        orderable=False,
        verbose_name=SELECT_ALL_CHECKBOX,
        attrs={'th': {'class': 'min-width-col centered'}, 'td': {'class': 'min-width-col centered'}},
    )
    report_id = tables.TemplateColumn(
        REPORT_ID_TEMPLATE,
        order_by='id',
        verbose_name='ID',
        attrs={'th': {'class': 'min-width-col'}, 'td': {'class': 'min-width-col'}},
    )
    host = tables.Column(
        accessor='host',
        verbose_name='Host',
        attrs={'th': {'class': 'col-sm-3'}, 'td': {'class': 'col-sm-3'}},
    )
    created = tables.Column(
        verbose_name='Created',
        attrs={'th': {'class': 'col-sm-3'}, 'td': {'class': 'col-sm-3'}},
    )
    report_ip = tables.Column(
        verbose_name='IP Address',
        attrs={'th': {'class': 'col-sm-2'}, 'td': {'class': 'col-sm-2'}},
    )
    processed = tables.TemplateColumn(
        PROCESSED_TEMPLATE,
        verbose_name='Processed',
        attrs={'th': {'class': 'col-sm-1'}, 'td': {'class': 'centered col-sm-1'}},
    )

    class Meta(BaseTable.Meta):
        model = Report
        fields = ('selection', 'report_id', 'host', 'created', 'report_ip', 'processed')
