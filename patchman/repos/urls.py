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

from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('patchman.repos.views',

    url(r'^$', 'repo_list', name='repo_list'),
    url(r'^(?P<repo_id>[-.\w]+)/$', 'repo_detail', name='repo_detail'),
    url(r'^(?P<repo_id>[-.\w]+)/delete/$', 'repo_delete', name='repo_delete'),
    url(r'^(?P<repo_id>[-.\w]+)/enable/$', 'repo_enable', name='repo_enable'),
    url(r'^(?P<repo_id>[-.\w]+)/disable/$', 'repo_disable', name='repo_disable'),
)
