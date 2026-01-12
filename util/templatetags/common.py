# Copyright 2013-2025 Marcus Furlong <furlongm@gmail.com>
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

import importlib
from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.template import Library
from django.template.loader import get_template
from django.utils.html import format_html
from django_tables2 import RequestConfig
from humanize import naturaltime

from util import get_setting_of_type

register = Library()


@register.simple_tag
def yes_no_img(boolean, alt_yes='Active', alt_no='Not Active'):
    if boolean:
        html = f'<span class="glyphicon glyphicon-ok" style="color: green;" title="{alt_yes}"></span>'
    else:
        html = f'<span class="glyphicon glyphicon-remove" style="color: red;" title="{alt_no}"></span>'
    return format_html(html)


@register.simple_tag
def no_yes_img(boolean, alt_yes='Not Required', alt_no='Required'):
    if not boolean:
        html = f'<span class="glyphicon glyphicon-ok" style="color: green;" title="{alt_yes}"></span>'
    else:
        html = f'<span class="glyphicon glyphicon-remove" style="color: red;" title="{alt_no}"></span>'
    return format_html(html)


@register.simple_tag(takes_context=True)
def gen_table(context, object_list, template_name=None):
    """Generate a django-tables2 table for non-paginated contexts (e.g., dashboard)."""
    if not object_list:
        return ''

    request = context.get('request')

    app_label = object_list.model._meta.app_label
    model_name = object_list.model.__name__

    app_mod = importlib.import_module(f"{app_label}.tables")
    TableClass = getattr(app_mod, f"{model_name}Table")

    table = TableClass(object_list)

    # Exclude selection column for embedded tables (dashboard, detail pages)
    if 'selection' in table.columns:
        table.columns.hide('selection')

    # No pagination for dashboard/detail page tables
    if request:
        RequestConfig(request, paginate=False).configure(table)

    # Render using the table's configured template
    from django.template import engines
    django_engine = engines['django']
    template = django_engine.from_string('{% load django_tables2 %}{% render_table table %}')
    return template.render({'table': table, 'request': request})


@register.simple_tag
def object_count(table):
    """Return object count string for django-tables2 table."""
    if hasattr(table, 'paginator') and table.paginator:
        count = table.paginator.count
        if count == 1:
            name = table.data.data.model._meta.verbose_name.title()
        else:
            name = table.data.data.model._meta.verbose_name_plural.title()
        return f'{count} {name}'
    return ''


@register.filter
def verbose_name_plural(table):
    """Return the verbose_name_plural from a django-tables2 table's model."""
    try:
        return table.data.data.model._meta.verbose_name_plural.title()
    except AttributeError:
        return ''


@register.simple_tag
def get_querydict(request):
    get = request.GET.copy()
    if 'page' in get:
        del get['page']
    if 'search' in get:
        del get['search']
    return get


@register.simple_tag
def get_querystring(request):
    get = request.GET.copy()
    if 'page' in get:
        del get['page']
    return urlencode(get)


@register.simple_tag
def searchform(terms, querydict):
    template = get_template('searchbar.html')
    html = template.render({'post_url': '.', 'terms': terms, 'querydict': querydict})
    return html


@register.simple_tag
def reports_timedelta():
    days = get_setting_of_type(
        setting_name='DAYS_WITHOUT_REPORT',
        setting_type=int,
        default=14,
    )
    return naturaltime(datetime.now() - timedelta(days=days))


@register.simple_tag
def host_count(osrelease):
    host_count = 0
    for osvariant in osrelease.osvariant_set.all():
        host_count += osvariant.host_set.count()
    return host_count
