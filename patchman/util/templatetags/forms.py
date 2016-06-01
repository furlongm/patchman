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


@register.simple_tag
def searchform(post_url="."):
    template = get_template('search_form.html')
    html = template.render({'post_url': post_url})
    return html
