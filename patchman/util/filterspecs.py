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


from django.utils.safestring import mark_safe
from django.db.models.query import QuerySet
from operator import itemgetter


def get_query_string(qs):
    newqs = [u'%s=%s' % (k, v) for k, v in qs.items()]
    return '?' + '&amp;'.join(newqs).replace(' ', '%20')


class Filter(object):
    multi = False

    def __init__(self, request, name, filters, header=''):

        if header == '':
            self.header = name
        else:
            self.header = header

        if isinstance(filters, tuple):
            filters = dict(filters)

        if isinstance(filters, QuerySet):
            f = {}
            for i in filters:
                if isinstance(i, unicode):
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
            del(qs[self.name])

        output = ''
        output += '<div class="panel panel-default">\n'
        output += '<div class="panel-heading">%s</div>\n' \
                  % self.header.replace('_', ' ')
        output += '<div class="panel-body">\n'
        output += '<div class="list-group list-group-info">\n'
        filters = sorted(self.filters.iteritems(), key=itemgetter(1))

        if self.selected is not None:
            output += '<a href="%s" class="list-group-item">all</a>\n' \
                      % get_query_string(qs)
        else:
            output += '<a href="%s" class="list-group-item ' \
                      % get_query_string(qs)
            output += 'list-group-item-success">all</a>\n'
        for k, v in filters:
            if str(self.selected) == str(k):
                style = "list-group-item-success"
            else:
                style = ''
            qs[self.name] = k
            output += '<a href="%s" class="list-group-item %s">%s</a>\n' \
                      % (get_query_string(qs), style, v)
        output += '</div></div></div>'
        return output


class FilterBar(object):

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
            if f.multi:
                params = dict(request.GET.items())
                generic = '%s__' % f.name
                m_params = \
                {k: v for k, v in params.items() if k.startswith(generic)}
                for k, v in m_params.items():
                    qs[k] = v

            else:
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
