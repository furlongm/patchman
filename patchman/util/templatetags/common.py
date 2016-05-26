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
from django.utils.html import format_html, escape
from django.conf import settings

register = Library()


@register.simple_tag
def active(request, pattern):
    import re
    if re.search('^%s/%s' % (request.META['SCRIPT_NAME'], pattern),
                 request.path):
        return 'active'
    return ''


@register.simple_tag
def yes_no_img(boolean, alt_yes='Active', alt_no='Not Active'):
    if boolean:
        return format_html("<img src='{}img/admin/icon-yes.gif' alt='{}' />",
                           escape(settings.STATIC_URL), escape(alt_yes))
    else:
        return format_html("<img src='{}img/admin/icon-no.gif' alt='{}' />",
                           escape(settings.STATIC_URL), escape(alt_no))


@register.simple_tag
def no_yes_img(boolean, alt_yes='Not Required', alt_no='Required'):
    if not boolean:
        return format_html("<img src='{}img/admin/icon-yes.gif' alt='{}' />",
                           escape(settings.STATIC_URL), escape(alt_yes))
    else:
        return format_html("<img src='{}img/admin/icon-no.gif' alt='{}' />",
                           escape(settings.STATIC_URL), escape(alt_no))


@register.simple_tag
def gen_table(queryset, template_name=None):
    if not template_name:
        app_label = queryset.model._meta.app_label
        model_name = queryset.model._meta.verbose_name
        template_name = '%s/%s_table.html' % \
            (app_label, model_name.lower().replace(' ', ''))
    template = get_template(template_name)
    html = template.render({'object_list': queryset})
    return html
