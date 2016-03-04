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


from django.template import Library, Node, Variable, VariableDoesNotExist, \
    TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import get_template

register = Library()


@register.tag
def searchform(parser, token):
    try:
        tag_name, post_url = token.split_contents()
    except:
        try:
            tag_name = token.split_contents()
            post_url = '.'
        except:
            raise (TemplateSyntaxError,
                   "%r tag requires one or no arguments" %
                   token.contents.split()[0])
    return SearchFormNode(post_url)


class SearchFormNode(Node):
    def __init__(self, post_url):
        self.post_url = post_url

    def render(self, context):
        template = get_template('search_form.html')
        html = template.render({'post_url': self.post_url})
        return html


@register.inclusion_tag('form_as_div.html')
def form_as_div(form):
    return {'form': form, }


@register.tag
def formfield(parser, token):
    try:
        tag_name, field = token.split_contents()
    except:
        raise (TemplateSyntaxError,
               "%r tag requires exactly one argument" %
               token.contents.split()[0])
    return FormFieldNode(field)


class FormFieldNode(Node):
    def __init__(self, field):
        self.field = Variable(field)

    def get_formfield_template(self, class_name):
        try:
            template_name = 'formfield/%s.html' % class_name
            return get_template(template_name)
        except TemplateDoesNotExist:
            return get_template('formfield/default.html')

    def render(self, context):
        try:
            field = self.field.resolve(context)
        except VariableDoesNotExist:
            return ''

        label_class_names = []
        if field.field.required:
            label_class_names.append('required')

        widget_class_name = field.field.widget.__class__.__name__.lower()
        if widget_class_name == 'checkboxinput':
            label_class_names.append('vCheckboxLabel')

        class_str = label_class_names and u' class="%s"' % \
            u' '.join(label_class_names) or u''

        template = self.get_formfield_template(widget_class_name)
        html = template.render({'class': class_str, 'formfield': field})
        return html
