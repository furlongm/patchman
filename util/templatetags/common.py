# Copyright 2010 VPAC
# Copyright 2013-2021 Marcus Furlong <furlongm@gmail.com>
#
# This file is part of Patchman.
#
# Patchman is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Patchman is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchman  If not, see <http://www.gnu.org/licenses/>.

import re

from humanize import naturaltime
from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.template import Library
from django.template.loader import get_template
from django.utils.html import format_html
from django.templatetags.static import static
from django.core.paginator import Paginator

from util import get_setting_of_type

register = Library()


@register.simple_tag
def active(request, pattern):
    if re.search(fr"^{request.META['SCRIPT_NAME']}/{pattern}", request.path):
        return 'active'
    return ''


@register.simple_tag
def yes_no_img(boolean, alt_yes='Active', alt_no='Not Active'):
    yes_icon = static('img/icon-yes.gif')
    no_icon = static('img/icon-no.gif')
    if boolean:
        html = f'<img src="{yes_icon}" alt="{alt_yes}" />'
    else:
        html = f'<img src="{no_icon}" alt="{alt_no}" />'
    return format_html(html)


@register.simple_tag
def no_yes_img(boolean, alt_yes='Not Required', alt_no='Required'):
    yes_icon = static('img/icon-yes.gif')
    no_icon = static('img/icon-no.gif')
    if not boolean:
        html = f'<img src="{yes_icon}" alt="{alt_yes}" />'
    else:
        html = f'<img src="{no_icon}" alt="{alt_no}" />'
    return format_html(html)


@register.simple_tag
def gen_table(object_list, template_name=None):
    if not object_list:
        return ''
    if not template_name:
        app_label = object_list.model._meta.app_label
        model_name = object_list.model._meta.verbose_name.replace(' ', '')
        template_name = f'{app_label}/{model_name.lower()}_table.html'
    template = get_template(template_name)
    html = template.render({'object_list': object_list})
    return html


@register.simple_tag
def object_count(page):
    if isinstance(page.paginator, Paginator):
        if page.paginator.count == 1:
            name = page.paginator.object_list.model._meta.verbose_name
        else:
            name = page.paginator.object_list.model._meta.verbose_name_plural
    return f'{page.paginator.count} {name}'


@register.simple_tag
def get_querystring(request):
    get = request.GET.copy()
    if 'page' in get:
        del get['page']
    return urlencode(get)


@register.simple_tag
def searchform(terms):
    template = get_template('searchbar.html')
    html = template.render({'post_url': '.', 'terms': terms})
    return html


@register.simple_tag
def reports_timedelta():
    days = get_setting_of_type(
        setting_name='DAYS_WITHOUT_REPORT',
        setting_type=int,
        default=14,
    )
    return naturaltime(datetime.now() - timedelta(days=days))
