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

from security import views

app_name = 'security'

urlpatterns = [
    path('', views.security_landing, name='security_landing'),
    path('cves', views.cve_list, name='cve_list'),
    path('cves/<str:cve_id>', views.cve_detail, name='cve_detail'),
    path('cwes', views.cwe_list, name='cwe_list'),
    path('cwes/<str:cwe_id>', views.cwe_detail, name='cwe_detail'),
]
