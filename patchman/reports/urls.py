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

urlpatterns = patterns('patchman.reports.views',

    url(r'^$', 'report_list', name='report_list' ),
    url(r'^upload/$', 'upload'),
    url(r'^(?P<report>[-.\w]+)/$', 'report_detail', name='report_detail' ),
    url(r'^(?P<report>[-.\w]+)/delete/$', 'report_delete', name='report_delete' ),
)
