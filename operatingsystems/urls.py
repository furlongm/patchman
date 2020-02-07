# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2016 Marcus Furlong <furlongm@gmail.com>
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

from __future__ import unicode_literals

from django.conf.urls import url

from operatingsystems import views

app_name = 'operatingsystems'

urlpatterns = [
    url(r'^$', views.os_list, name='os_list'),
    url(r'^groups/$', views.osgroup_list, name='osgroup_list'),
    url(r'^(?P<os_id>[-.\w]+)/$', views.os_detail, name='os_detail'),
    url(r'^(?P<os_id>[-.\w]+)/delete/$', views.os_delete, name='os_delete'),
    url(r'^groups/(?P<osgroup_id>[-.\w]+)/$', views.osgroup_detail,
        name='osgroup_detail'),
    url(r'^groups/(?P<osgroup_id>[-.\w]+)/delete/$', views.osgroup_delete,
        name='osgroup_delete'),
]
