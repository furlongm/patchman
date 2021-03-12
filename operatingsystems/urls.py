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

from django.urls import path

from operatingsystems import views

app_name = 'operatingsystems'

urlpatterns = [
    path('', views.os_list, name='os_list'),
    path('<int:os_id>/', views.os_detail, name='os_detail'),
    path('<int:os_id>/delete/', views.os_delete, name='os_delete'),
    path('groups/', views.osgroup_list, name='osgroup_list'),
    path('groups/<int:osgroup_id>/', views.osgroup_detail, name='osgroup_detail'),  # noqa
    path('groups/<int:osgroup_id>/delete/', views.osgroup_delete, name='osgroup_delete'),  # noqa
]
