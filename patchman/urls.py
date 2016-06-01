# Copyright 2012 VPAC, http://www.vpac.org
#
# This file is part of patchman
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
# along with  If not, see <http://www.gnu.org/licenses/>

from django.conf.urls import url, include, handler404, handler500
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views
from django.views import static

admin.autodiscover()

urlpatterns = [

    url(r'^', include('django.contrib.auth.urls')),
    url(r'^', include('patchman.util.urls')),
    url(r'^reports/', include('patchman.reports.urls')),
    url(r'^hosts/', include('patchman.hosts.urls')),
    url(r'^packages/', include('patchman.packages.urls')),
    url(r'^repos/', include('patchman.repos.urls')),
    url(r'^os/', include('patchman.operatingsystems.urls')),
    url(r'^admin/', include(admin.site.urls)),
]

if settings.DEBUG:
    urlpatterns += [
        url(r'^patchman_media/(?P<path>.*)$', static.serve),
    ]
