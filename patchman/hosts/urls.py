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

from django.conf.urls import patterns, url

urlpatterns = patterns('patchman.hosts.views',

    url(r'^$', 'host_list', name='host_list'),
    url(r'^(?P<hostname>[-.\w]+)/$', 'host_detail', name='host_detail'),
    url(r'^(?P<hostname>[-.\w]+)/delete/$', 'host_delete', name='host_delete'),
    url(r'^(?P<hostname>[-.\w]+)/edit/$', 'host_edit', name='host_edit'),
)
