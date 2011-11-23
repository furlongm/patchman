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

from django.conf.urls.defaults import patterns, url, include, handler404, handler500
from django.conf import settings
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',

    url(r'^$', 'patchman.views.dashboard', name='dashboard'),
    url(r'^reports/', include('patchman.reports.urls')),
    url(r'^hosts/', include('patchman.hosts.urls')),
    url(r'^packages/', include('patchman.packages.urls')),
    url(r'^repos/', include('patchman.repos.urls')),
    url(r'^os/', include('patchman.operatingsystems.urls')),
    url(r'^reports/', include('patchman.reports.urls')),
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', name='login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', name='logout'),
    # Uncomment the admin/doc line below to enable admin documentation:
    #(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    (r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^patchman_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )
