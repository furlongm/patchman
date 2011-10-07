# Copyright 2011 VPAC <furlongm@vpac.org>
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

from django.forms import ModelForm, ModelMultipleChoiceField
from django.contrib.admin.widgets import FilteredSelectMultiple
from patchman.operatingsystems.models import OS, OSGroup
from patchman.repos.models import Repository

class LinkOSGroupForm(ModelForm):

    class Meta:
        model = OS
        fields = ('osgroup',)

class AddReposToOSGroupForm(ModelForm):

    repos = ModelMultipleChoiceField(queryset=Repository.objects.select_related(), required=False, label=None, widget=FilteredSelectMultiple('Repos', False))

    class Meta:
        model = OSGroup
        fields = ('repos',)

