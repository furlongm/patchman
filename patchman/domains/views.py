# Copyright 2016 Marcus Furlong <furlongm@gmail.com>
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
from rest_framework import viewsets

from patchman.domains.models import Domain
from patchman.domains.serializers import DomainSerializer


#@login_required
class DomainViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows package architectures to be viewed or edited.
    """
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
