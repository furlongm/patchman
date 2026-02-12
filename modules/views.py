# Copyright 2023 Marcus Furlong <furlongm@gmail.com>
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

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django_tables2 import RequestConfig
from rest_framework import permissions, viewsets

from modules.models import Module
from modules.serializers import ModuleSerializer
from modules.tables import ModuleTable


@login_required
def module_list(request):

    modules = Module.objects.select_related('arch', 'repo')

    if 'search' in request.GET:
        terms = request.GET['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(name__icontains=term)
            query = query & q
        modules = modules.filter(query)
    else:
        terms = ''

    table = ModuleTable(modules)
    RequestConfig(request, paginate={'per_page': 50}).configure(table)

    return render(request,
                  'modules/module_list.html',
                  {'table': table,
                   'terms': terms})


@login_required
def module_detail(request, module_id):

    module = get_object_or_404(Module, id=module_id)
    return render(request,
                  'modules/module_detail.html',
                  {'module': module})


class ModuleViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows modules to be viewed or edited.
    """
    queryset = Module.objects.select_related('arch', 'repo').all()
    serializer_class = ModuleSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
