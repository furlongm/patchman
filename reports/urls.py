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

from reports import views

app_name = 'reports'

urlpatterns = [
    url(r'^$', views.report_list, name='report_list'),
    url(r'^upload/$', views.upload),
    url(r'^(?P<report>[-.\w]+)/$', views.report_detail,
        name='report_detail'),
    url(r'^(?P<report>[-.\w]+)/delete/$', views.report_delete,
        name='report_delete'),
    url(r'^(?P<report>[-.\w]+)/process/$', views.report_process,
        name='report_process'),
]
