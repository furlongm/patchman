from django.forms import ModelForm, ModelMultipleChoiceField
from django.contrib.admin.widgets import FilteredSelectMultiple
from patchman.operatingsystems.models import OS, OSGroup
from patchman.repos.models import Repository

class LinkOSGroupForm(ModelForm):

    class Meta:
        model = OS
        fields = ('osgroup',)

class AddReposToOSGroupForm(ModelForm):

    repos = ModelMultipleChoiceField(queryset=Repository.objects.select_related(), widget=FilteredSelectMultiple('Repos', False))

    class Meta:
        model = OSGroup
        fields = ('repos',)

