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

from repos import views

app_name = 'repos'

urlpatterns = [
    url(r'^$', views.repo_list, name='repo_list'),
    url(r'^(?P<repo_id>[-.\w]+)/delete/$', views.repo_delete,
        name='repo_delete'),
    url(r'^(?P<repo_id>[-.\w]+)/toggle_enabled/$', views.repo_toggle_enabled,
        name='repo_toggle_enabled'),
    url(r'^(?P<repo_id>[-.\w]+)/toggle_security/$', views.repo_toggle_security,
        name='repo_toggle_security'),
    url(r'^(?P<repo_id>[-.\w]+)/edit/$', views.repo_edit, name='repo_edit'),
    url(r'^mirrors/$', views.mirror_list, name='mirror_list'),
    url(r'^(?P<repo_id>[-.\w]+)/$', views.repo_detail, name='repo_detail'),
    url(r'^mirrors/mirror/(?P<mirror_id>[-.\w]+)/$',
        views.mirror_detail, name='mirror_detail'),
    url(r'^mirrors/mirror/(?P<mirror_id>[-.\w]+)/delete/$',
        views.mirror_delete, name='mirror_delete'),
    url(r'^mirrors/mirror/(?P<mirror_id>[-.\w]+)/edit/$',
        views.mirror_edit, name='mirror_edit'),
]
