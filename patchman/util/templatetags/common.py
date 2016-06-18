# Copyright 2010 VPAC
#
# This file is part of django-andsome.
#
# django-andsome is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-andsome is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with django-andsome  If not, see <http://www.gnu.org/licenses/>.

from django.template import Library
from django.template.loader import get_template
from django.utils.html import format_html
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.paginator import QuerySetPaginator

try:
    from urllib.parse import urlencode
except ImportError:
     from urllib import urlencode

register = Library()


@register.simple_tag
def active(request, pattern):
    import re
    if re.search('^{0!s}/{1!s}'.format(request.META['SCRIPT_NAME'], pattern),
                 request.path):
        return 'active'
    return ''


@register.simple_tag
def yes_no_img(boolean, alt_yes='Active', alt_no='Not Active'):
    yes_icon = static('img/icon-yes.gif')
    no_icon = static('img/icon-no.gif')
    if boolean:
        html = "<img src='{0!s}' alt='{1!s}' />".format(yes_icon, alt_yes)
    else:
        html = "<img src='{0!s}' alt='{1!s}' />".format(no_icon, alt_no)
    return format_html(html)


@register.simple_tag
def no_yes_img(boolean, alt_yes='Not Required', alt_no='Required'):
    yes_icon = static('img/icon-yes.gif')
    no_icon = static('img/icon-no.gif')
    if not boolean:
        html = "<img src='{0!s}' alt='{1!s}' />".format(yes_icon, alt_yes)
    else:
        html = "<img src='{0!s}' alt='{1!s}' />".format(no_icon, alt_no)
    return format_html(html)


@register.simple_tag
def gen_table(object_list, template_name=None):
    if object_list == '':
        return ''
    if not template_name:
        app_label = object_list.model._meta.app_label
        model_name = object_list.model._meta.verbose_name
        template_name = '{0!s}/{1!s}_table.html'.format(app_label, model_name.lower().replace(' ', ''))
    template = get_template(template_name)
    html = template.render({'object_list': object_list})
    return html


@register.simple_tag
def object_count(page):
    if isinstance(page.paginator, QuerySetPaginator):
        if page.paginator.count == 1:
            name = page.paginator.object_list.model._meta.verbose_name
        else:
            name = page.paginator.object_list.model._meta.verbose_name_plural
    return '{0!s} {1!s}'.format(page.paginator.count, name)


@register.assignment_tag
def get_querystring(request):
    get = request.GET.copy()
    if 'page' in get:
        del get['page']
    return urlencode(get)


@register.simple_tag
def searchform(post_url="."):
    template = get_template('searchbar.html')
    html = template.render({'post_url': post_url})
    return html
