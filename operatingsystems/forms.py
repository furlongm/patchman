# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2021 Marcus Furlong <furlongm@gmail.com>
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

from operatingsystems.models import OS, OSGroup
from repos.models import Repository


class AddOSToOSGroupForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(AddOSToOSGroupForm, self).__init__(*args, **kwargs)
        self.fields['osgroup'].label = 'OS Groups'

    class Meta(object):
        model = OS
        fields = ('osgroup',)


class CreateOSGroupForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(CreateOSGroupForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = 'New OS Group'

    class Meta(object):
        model = OSGroup
        fields = ('name',)


class AddReposToOSGroupForm(ModelForm):

    repos = ModelMultipleChoiceField(
        queryset=Repository.objects.select_related(),
        required=False,
        label=None,
        widget=FilteredSelectMultiple('Repos', False))

    def __init__(self, *args, **kwargs):
        super(AddReposToOSGroupForm, self).__init__(*args, **kwargs)
        self.fields['repos'].label = ''

    class Meta(object):
        model = OSGroup
        fields = ('repos',)
