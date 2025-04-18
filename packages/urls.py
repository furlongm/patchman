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

from packages import views

app_name = 'packages'

urlpatterns = [
    path('', views.package_name_list, name='package_name_list'),
    path('name/', views.package_name_list, name='package_name_list'),
    path('name/<str:packagename>/', views.package_name_detail, name='package_name_detail'),
    path('id/', views.package_list, name='package_list'),
    path('id/<int:package_id>/', views.package_detail, name='package_detail'),
]
