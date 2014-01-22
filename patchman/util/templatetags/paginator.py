# Copyright 2010 VPAC
#
# This file is part of django-andsom.
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
from django.utils.safestring import mark_safe
from django.core.paginator import QuerySetPaginator
from andsome.util.filterspecs import get_query_string

register = template.Library()

DOT = '.'

def paginator_number(page, i, qs):

    qs['page'] = i
    
    if i == DOT:
        return u'... '
    elif i == page.number:
        return mark_safe(u'<span class="this-page">%d</span> ' % (i))
    else:
        return mark_safe(u'<a href="%s"%s>%d</a> ' % ((get_query_string(qs)), (i == page.paginator.num_pages and ' class="end"' or ''), i))
paginator_number = register.simple_tag(paginator_number)

def pagination(page, request, eitherside=10):
    
    tqs = request.META['QUERY_STRING']
    qs = {}
    try:
        tqs = tqs.split('&')
        for q in tqs:
            k, v = q.split('=')
            qs[k] = v
    except:
        pass
    pagination_required = False
    if page.paginator.num_pages > 1:
        pagination_required = True
      
    if page.paginator.count == 1:
        object_name = 'object'
    else:
        object_name = 'objects'

    if isinstance(page.paginator, QuerySetPaginator):
        if page.paginator.count == 1:
            object_name = page.paginator.object_list.model._meta.verbose_name
        else:
            object_name = page.paginator.object_list.model._meta.verbose_name_plural

    if not pagination_required:
        page_range = []
    else:

        ON_EACH_SIDE = 3
        ON_ENDS = 2

        # If there are 10 or fewer pages, display links to every page.
        # Otherwise, do some fancy
        if page.paginator.num_pages <= 10:
            page_range = range(1, page.paginator.num_pages + 1)
        else:
            # Insert "smart" pagination links, so that there are always ON_ENDS
            # links at either end of the list of pages, and there are always
            # ON_EACH_SIDE links at either end of the "current page" link.
            page_range = []
            page_num = page.number
            if page_num > (ON_EACH_SIDE + ON_ENDS +1):
                page_range.extend(range(1, ON_EACH_SIDE))
                page_range.append(DOT)
                page_range.extend(range(page_num - ON_EACH_SIDE, page_num + 1))
            else:
                page_range.extend(range(1, page_num + 1))
            if page_num < (page.paginator.num_pages - ON_EACH_SIDE - ON_ENDS):
                page_range.extend(range(page_num + 1, page_num + ON_EACH_SIDE + 1))
                page_range.append(DOT)
                page_range.extend(range(page.paginator.num_pages - ON_ENDS + 1, page.paginator.num_pages + 1))
            else:
                page_range.extend(range(page_num + 1, page.paginator.num_pages + 1))

    return {
        'page': page,
        'pagination_required': pagination_required,
        'object_name': object_name,
        'qs': qs,
        'page_list': page_range,
    }
pagination = register.inclusion_tag('pagination.html')(pagination)
