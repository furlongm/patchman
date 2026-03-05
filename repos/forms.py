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

from django.forms import (
    Form, ModelChoiceField, ModelForm, ModelMultipleChoiceField, TextInput,
    ValidationError,
)
from django_select2.forms import ModelSelect2MultipleWidget

from repos.models import Mirror, Repository


class MirrorSelect2Widget(ModelSelect2MultipleWidget):
    model = Mirror
    search_fields = ['url__icontains', 'repo__name__icontains']
    max_results = 50
    queryset = Mirror.objects.select_related('repo').order_by('repo__name', 'url')

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {})
        kwargs['attrs'].setdefault('data-minimum-input-length', 0)
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        return f"{obj.repo.name} - {obj.url}"


class EditRepoForm(ModelForm):
    mirrors = ModelMultipleChoiceField(
        queryset=Mirror.objects.select_related('repo').order_by('repo__name', 'url'),
        required=False,
        widget=MirrorSelect2Widget(attrs={'style': 'width: 100%'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget = TextInput(attrs={'size': 100})
        self.fields['repo_id'].widget = TextInput(attrs={'size': 100})

    class Meta:
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
        super().__init__(*args, **kwargs)
        self.arch = arch
        self.repotype = repotype
        self.fields['name'].label = 'New Repository'

    class Meta:
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['url'].widget = TextInput(attrs={'size': 150},)
        self.fields['packages_checksum'].widget = TextInput(attrs={'size': 100},)

    class Meta:
        model = Mirror
        fields = ('repo', 'url', 'enabled', 'refresh', 'mirrorlist',
                  'last_access_ok', 'fail_count', 'packages_checksum')
