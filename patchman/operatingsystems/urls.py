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

from django.conf.urls.defaults import *

urlpatterns = patterns('patchman.operatingsystems.views',

    url(r'^$', 'os_list', name='os_list' ),
    url(r'^groups/$', 'osgroup_list', name= 'osgroup_list'),
    url(r'^(?P<os_id>[-.\w]+)/$', 'os_detail', name='os_detail' ),
    url(r'^groups/(?P<osgroup_id>[-.\w]+)/$', 'osgroup_detail', name='osgroup_detail' ),
)
