# Copyright 2010 VPAC
# Copyright 2014-2025 Marcus Furlong <furlongm@gmail.com>
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

from operator import itemgetter

from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe


def get_query_string(qs):
    new_qs = [f'{k}={v}' for k, v in list(qs.items())]
    return '?' + '&amp;'.join(new_qs).replace(' ', '%20')


class Filter:

    def __init__(self, request, header, name, filters):
        self.header = header

        if isinstance(filters, tuple):
            filters = dict(filters)

        if isinstance(filters, QuerySet):
            f = {}
            for i in filters:
                if isinstance(i, str):
                    f[str(i)] = str(i)
                else:
                    f[i.pk] = str(i)
            filters = f

        self.name = name
        self.filters = filters
        self.selected = None
        if self.name in request.GET:
            self.selected = request.GET[self.name]

    def output(self, qs):
        if self.name in qs:
            del qs[self.name]

        output = '<div class="panel panel-default">\n'
        output += f'<div class="panel-heading">{self.header}</div>\n'
        output += '<div class="panel-body">\n'
        output += '<div class="list-group list-group-info">\n'
        output += f'<a href="{get_query_string(qs)}" '
        output += 'class="list-group-item'
        if self.selected is None:
            output += ' list-group-item-success'
        output += '">Unfiltered</a>\n'

        filters = sorted(iter(self.filters.items()), key=itemgetter(1))
        for k, v in filters:
            style = ''
            if str(self.selected) == str(k):
                style = 'list-group-item-success'
            qs[self.name] = k
            output += f'<a href="{get_query_string(qs)}" class='
            output += f'"list-group-item {style}">{v}</a>\n'
        output += '</div></div></div>'
        return output


class FilterBar:

    def __init__(self, request, filter_list):
        self.request = request
        self.filter_list = filter_list
        raw_qs = request.META.get('QUERY_STRING', '')
        qs = {}
        if raw_qs:
            for i in raw_qs.replace('?', '').split('&'):
                if i:
                    k, v = i.split('=')
                    if k != 'page':
                        qs[k] = v
        for f in self.filter_list:
            if f.name in self.request.GET:
                qs[f.name] = self.request.GET[f.name]
        self.qs = qs

    def output(self):
        output = ''
        for f in self.filter_list:
            output += f.output(self.qs.copy())
        return output

    def __str__(self):
        return mark_safe(self.output())
