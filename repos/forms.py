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

from django.forms import ModelForm, ModelMultipleChoiceField, TextInput, \
    Form, ModelChoiceField, ValidationError
from django.contrib.admin.widgets import FilteredSelectMultiple

from repos.models import Repository, Mirror


class EditRepoForm(ModelForm):
    class Media(object):
        css = {
            'all': ('admin/css/widgets.css',)
        }

    mirrors = ModelMultipleChoiceField(
        queryset=Mirror.objects.select_related(),
        required=False,
        label=None,
        widget=FilteredSelectMultiple('Mirrors', is_stacked=False))

    def __init__(self, *args, **kwargs):
        super(EditRepoForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget = TextInput(attrs={'size': 100})
        self.fields['repo_id'].widget = TextInput(attrs={'size': 100})

    class Meta(object):
        model = Repository
        fields = ('name', 'repo_id', 'repotype', 'arch', 'security', 'enabled',
                  'mirrors', 'auth_required')


class LinkRepoForm(Form):

    name = ModelChoiceField(
        queryset=Repository.objects.order_by('name'),
        label='Repositories')


class CreateRepoForm(ModelForm):

    def __init__(self, *args, **kwargs):
        arch = kwargs.pop('arch', False)
        repotype = kwargs.pop('repotype', False)
        super(CreateRepoForm, self).__init__(*args, **kwargs)
        self.arch = arch
        self.repotype = repotype
        self.fields['name'].label = 'New Repository'

    class Meta(object):
        model = Repository
        fields = ('name',)

    def clean_arch(self):
        data = self.cleaned_data['arch']
        if data != self.arch:
            text = 'Not all Mirror architectures are the same, cannot proceed'
            raise ValidationError(text)
        return data

    def clean_repotype(self):
        data = self.cleaned_data['repotype']
        if data != self.repotype:
            text = 'Not all Mirror repotypes are the same, cannot proceed'
            raise ValidationError(text)
        return data


class EditMirrorForm(ModelForm):
    class Media(object):
        css = {
            'all': ('admin/css/widgets.css',)
        }
        js = ('animations.js', 'actions.js')

    def __init__(self, *args, **kwargs):
        super(EditMirrorForm, self).__init__(*args, **kwargs)
        self.fields['url'].widget = TextInput(attrs={'size': 150},)
        self.fields['file_checksum'].widget = TextInput(attrs={'size': 100},)

    class Meta(object):
        model = Mirror
        fields = ('repo', 'url', 'enabled', 'refresh', 'mirrorlist',
                  'last_access_ok', 'fail_count', 'file_checksum')
