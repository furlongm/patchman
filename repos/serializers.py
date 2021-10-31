# Copyright 2016-2021 Marcus Furlong <furlongm@gmail.com>
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

from repos.models import Repository, Mirror, MirrorPackage


class RepositorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = Repository
        fields = ('id', 'name', 'arch', 'security', 'repotype', 'enabled',
                  'auth_required')


class MirrorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = Mirror
        fields = ('id', 'repo', 'url', 'last_access_ok', 'file_checksum',
                  'timestamp', 'mirrorlist', 'enabled', 'refresh',
                  'fail_count')


class MirrorPackageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(object):
        model = MirrorPackage
        fields = ('id', 'mirror', 'package', 'enabled')
