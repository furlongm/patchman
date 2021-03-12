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

from repos import views

app_name = 'repos'

urlpatterns = [
    path('', views.repo_list, name='repo_list'),
    path('<int:repo_id>/', views.repo_detail, name='repo_detail'),
    path('<int:repo_id>/toggle_enabled/', views.repo_toggle_enabled, name='repo_toggle_enabled'),  # noqa
    path('<int:repo_id>/toggle_security/', views.repo_toggle_security, name='repo_toggle_security'),  # noqa
    path('<int:repo_id>/edit/', views.repo_edit, name='repo_edit'),
    path('<int:repo_id>/delete/', views.repo_delete, name='repo_delete'),
    path('mirrors/', views.mirror_list, name='mirror_list'),
    path('mirrors/mirror/<int:mirror_id>/', views.mirror_detail, name='mirror_detail'),  # noqa
    path('mirrors/mirror/<int:mirror_id>/edit/', views.mirror_edit, name='mirror_edit'),  # noqa
    path('mirrors/mirror/<int:mirror_id>/delete/', views.mirror_delete, name='mirror_delete'),  # noqa
]
