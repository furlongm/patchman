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


from django import template
from django.conf import settings
from django.utils.html import format_html, escape

register = template.Library()


@register.simple_tag
def active(request, pattern):
    import re
    if re.search('^%s/%s' % (request.META['SCRIPT_NAME'], pattern), request.path):
        return 'active'
    return ''


@register.simple_tag
def yes_no_img(boolean, reversed=False, alt_true='Active', alt_false='Not Active'):

    if reversed == 'reversed':
        if boolean:
            boolean = False
        else:
            boolean = True

    if boolean:
        return format_html("<img src='{}/img/admin/icon-yes.gif' alt='{}' />", escape(settings.STATIC_URL), escape(alt_true))
    else:
        return format_html("<img src='{}/img/admin/icon-no.gif' alt='{}' />", escape(settings.STATIC_URL), escape(alt_false))


@register.tag
def gen_table(parser, token):
    try:
        tag_name, queryset, template_name = token.split_contents()
    except:
        try:
            tag_name, queryset = token.split_contents()
            template_name = None
        except:
            raise template.TemplateSyntaxError, "%r tag requires one or two arguments" % token.contents.split()[0]
    return QuerySetTableNode(queryset, template_name)


class QuerySetTableNode(template.Node):

    def __init__(self, queryset, template_name):
        self.queryset = template.Variable(queryset)
        self.template_name = template_name

    def render(self, context):
        try:
            queryset = self.queryset.resolve(context)
        except template.VariableDoesNotExist:
            return ''

        if not self.template_name:
            app_label = queryset.model._meta.app_label
            model_name = queryset.model._meta.verbose_name
            template_name = '%s/%s_table.html' % (app_label, model_name.lower().replace(' ', ''))
        else:
            template_name = self.template_name
        template_obj = template.loader.get_template(template_name)

        context.push()
        context['object_list'] = queryset
        output = template_obj.render(context.flatten())
        context.pop()
        return output
