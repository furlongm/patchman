# Copyright 2016-2021 Marcus Furlong <furlongm@gmail.com>
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

from rest_framework import viewsets, permissions

from arch.models import PackageArchitecture, MachineArchitecture
from arch.serializers import PackageArchitectureSerializer, \
    MachineArchitectureSerializer


class PackageArchitectureViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows package architectures to be viewed or edited.
    """
    queryset = PackageArchitecture.objects.all()
    serializer_class = PackageArchitectureSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class MachineArchitectureViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows machine architectures to be viewed or edited.
    """
    queryset = MachineArchitecture.objects.all()
    serializer_class = MachineArchitectureSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
