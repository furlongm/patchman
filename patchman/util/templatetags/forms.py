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
from django.conf import settings
from django import template

register = Library()


@register.inclusion_tag('inlineformfield.html')
def inlineformfield(field1, field2, field3=False):
    return locals()

@register.inclusion_tag('checkbox_formfield.html')
def checkbox_formfield(field):
    return {'field': field, }

@register.inclusion_tag('form_as_div.html')
def form_as_div(form):
    return {'form': form, }

@register.inclusion_tag('search_form.html')
def search_form(url='', terms=''):
    return { 'url': url, 'terms': terms, 'STATIC_URL': settings.STATIC_URL }


@register.tag
def formfield(parser, token):
    try:
        tag_name, field = token.split_contents()
    except:
        raise template.TemplateSyntaxError, "{0!r} tag requires exactly one argument".format(token.contents.split()[0])
    return FormFieldNode(field)


class FormFieldNode(template.Node):
    def __init__(self, field):
        self.field = template.Variable(field)

    def get_template(self, class_name):
        try:
            template_name = 'formfield/{0!s}.html'.format(class_name)
            return template.loader.get_template(template_name)
        except template.TemplateDoesNotExist:
            return template.loader.get_template('formfield/default.html')

    def render(self, context):
        try:
            field = self.field.resolve(context)
        except template.VariableDoesNotExist:
            return ''

        label_class_names = []
        if field.field.required:
            label_class_names.append('required')

        widget_class_name = field.field.widget.__class__.__name__.lower()
        if widget_class_name == 'checkboxinput':
            label_class_names.append('vCheckboxLabel')


        class_str = label_class_names and u' class="{0!s}"'.format(u' '.join(label_class_names)) or u''

        context.push()
        context.push()
        context['class'] = class_str
        context['formfield'] = field
        output = self.get_template(widget_class_name).render(context)
        context.pop()
        context.pop()
        return output





