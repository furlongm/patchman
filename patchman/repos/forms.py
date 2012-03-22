# Copyright 2012 VPAC, http://www.vpac.org
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

from django.forms import ModelForm, ModelMultipleChoiceField, TextInput, Form, ModelChoiceField, ValidationError
from django.contrib.admin.widgets import FilteredSelectMultiple

from patchman.repos.models import Repository, Mirror


class RepositoryForm(ModelForm):

    mirrors = ModelMultipleChoiceField(queryset=Mirror.objects.select_related(), required=False, label=None, widget=FilteredSelectMultiple('Mirrors', True))

    def __init__(self, *args, **kwargs):
        super(RepositoryForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget = TextInput(attrs={'size': 100})

    class Meta:
        model = Repository
        fields = ('name', 'repotype', 'arch', 'security', 'enabled', 'mirrors', )


class LinkRepoForm(Form):

    name = ModelChoiceField(queryset=Repository.objects.order_by('name'), label='Link all mirrors above to an existing Repository')
    
        
class CreateRepoForm(ModelForm):

    def __init__(self, *args, **kwargs):
        arch = kwargs.pop('arch', False)
        repotype = kwargs.pop('repotype', False)
        super(CreateRepoForm, self).__init__(*args, **kwargs)
        self.arch = arch
        self.repotype = repotype
        self.fields['name'].label = 'Or create a new Repository named'

    class Meta:
        model = Repository
        fields = ('name',)

    def clean_arch(self):
        data = self.cleaned_data['arch']
        if data != self.arch:
            raise ValidationError("Not all mirror architectures are the same, cannot proceed.")
        return data

    def clean_repotype(self):
        data = self.cleaned_data['repotype']
        if data != self.repotype:
            raise ValidationError("Not all mirror repotypes are the same, cannot proceed.")
        return data
