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

from operatingsystems.models import OSVariant, OSRelease
from repos.models import Repository


class AddOSVariantToOSReleaseForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['osrelease'].label = 'OS Releases'

    class Meta:
        model = OSVariant
        fields = ('osrelease',)


class CreateOSReleaseForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = 'New OS Release'

    class Meta:
        model = OSRelease
        fields = ('name',)


class AddReposToOSReleaseForm(ModelForm):

    repos = ModelMultipleChoiceField(
        queryset=Repository.objects.select_related(),
        required=False,
        label=None,
        widget=FilteredSelectMultiple('Repos', False, attrs={'size':'30'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['repos'].label = ''

    class Meta:
        model = OSRelease
        fields = ('repos',)
