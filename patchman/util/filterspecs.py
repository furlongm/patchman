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
    return '?' + '&amp;'.join([u'%s=%s' % (k, v) for k, v in qs.items()]).replace(' ', '%20')


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
                f[str(i)] = str(i)
            filters = f

        if isinstance(filters, QuerySet):
            f = {}
            for i in filters:
                f[i.pk] = str(i)
            filters = f

        self.name = name
        self.filters = filters
        self.selected = None
        if name in request.GET:
            self.selected = request.GET[name]


    def output(self, qs):

        try:
            del(qs[self.name])
        except:
            pass

        output = ''
        output += '<h3>By %s</h3>\n' % self.header.replace('_', ' ')
        output += '<ul>\n'
        filters = sorted(self.filters.iteritems(), key=itemgetter(1))

        if self.selected is not None:
            output += """<li><a href="%s">All</a></li>\n""" % get_query_string(qs)
        else:
            output += """<li class="selected"><a href="%s">All</a></li>\n""" % get_query_string(qs)
        for k, v in filters:
            if str(self.selected) == str(k):
                style = """class="selected" """
            else:
                style = ""
            qs[self.name] = k
            output += """<li %s><a href="%s">%s</a></li>\n""" % (style, get_query_string(qs), v)

        output += '</ul>'

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
                field_generic = '%s__' % f.name
                m_params = {k: v for k, v in params.items() if k.startswith(field_generic)}
                for k, v in m_params.items():
                    qs[k] = v

            else:
                if name in self.request.GET:
                    qs[f.name] = self.request.GET[f.name]

        self.qs = qs

    def output(self):

        output = ''

        for f in self.filter_list:
            output += f.output(self.qs.copy())

        return output

    def __str__(self):
        return mark_safe(self.output())
