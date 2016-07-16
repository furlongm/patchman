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

from rest_framework import serializers

from patchman.hosts.models import Host, HostRepo


class HostSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = Host
        fields = ('id', 'hostname', 'ipaddress', 'reversedns', 'check_dns',
                  'os', 'kernel', 'arch', 'domain', 'lastreport', 'repos',
                  'updates', 'reboot_required', 'host_repos_only', 'tags',
                  'updated_at')


class HostRepoSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = HostRepo
        fields = ('host', 'repo', 'enabled', 'priority')
