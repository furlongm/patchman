# Copyright 2025 Marcus Furlong <furlongm@gmail.com>
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

from patchman.compliance import views

app_name = 'compliance'

urlpatterns = [
    path('', views.compliance_summary, name='compliance_summary'),
    path('host/<int:host_id>/', views.compliance_host, name='compliance_host'),
    path('rule/<int:rule_id>/', views.compliance_rule, name='compliance_rule'),
]
