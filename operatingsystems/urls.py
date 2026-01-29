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
    path('', views.os_landing, name='os_landing'),
    path('variants/', views.osvariant_list, name='osvariant_list'),
    path('variants/bulk_action/', views.osvariant_bulk_action, name='osvariant_bulk_action'),
    path('variants/<int:osvariant_id>/', views.osvariant_detail, name='osvariant_detail'),
    path('variants/<int:osvariant_id>/delete/', views.osvariant_delete, name='osvariant_delete'),
    path('variants/no_host/delete/', views.delete_nohost_osvariants, name='delete_nohost_osvariants'),
    path('releases/', views.osrelease_list, name='osrelease_list'),
    path('releases/bulk_action/', views.osrelease_bulk_action, name='osrelease_bulk_action'),
    path('releases/<int:osrelease_id>/', views.osrelease_detail, name='osrelease_detail'),
    path('releases/<int:osrelease_id>/delete/', views.osrelease_delete, name='osrelease_delete'),
]
