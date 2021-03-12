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

from django.forms import ModelForm, TextInput

from hosts.models import Host


class EditHostForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(EditHostForm, self).__init__(*args, **kwargs)
        self.fields['hostname'].widget = TextInput(attrs={'size': 50},)
        self.fields['reversedns'].widget = TextInput(attrs={'size': 50},)
        self.fields['kernel'].widget = TextInput(attrs={'size': 50},)

    class Meta(object):
        model = Host
        fields = ('hostname',
                  'reversedns',
                  'ipaddress',
                  'os',
                  'kernel',
                  'arch',
                  'reboot_required',
                  'host_repos_only',
                  'check_dns',
                  'tags')
