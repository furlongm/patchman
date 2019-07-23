# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2016 Marcus Furlong <furlongm@gmail.com>
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

from __future__ import unicode_literals

from django.conf.urls import url, include, handler404, handler500  # noqa
from django.conf import settings
from django.contrib import admin
from django.views import static

from rest_framework import routers

from arch import views as arch_views
from domains import views as domain_views
from hosts import views as host_views
from operatingsystems import views as os_views
from packages import views as package_views
from repos import views as repo_views

router = routers.DefaultRouter()
router.register(r'package-architecture', arch_views.PackageArchitectureViewSet)
router.register(r'machine-architecture', arch_views.MachineArchitectureViewSet)
router.register(r'domain', domain_views.DomainViewSet)
router.register(r'host', host_views.HostViewSet)
router.register(r'host-repo', host_views.HostRepoViewSet)
router.register(r'os', os_views.OSViewSet)
router.register(r'os-group', os_views.OSGroupViewSet)
router.register(r'package-name', package_views.PackageNameViewSet)
router.register(r'package', package_views.PackageViewSet)
router.register(r'package-update', package_views.PackageUpdateViewSet)
router.register(r'erratum', package_views.ErratumViewSet)
router.register(r'erratum-reference', package_views.ErratumReferenceViewSet)
router.register(r'repo', repo_views.RepositoryViewSet)
router.register(r'mirror', repo_views.MirrorViewSet)
router.register(r'mirror-package', repo_views.MirrorPackageViewSet)

admin.autodiscover()

urlpatterns = [
    url(r'^', include('django.contrib.auth.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^api/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),  # noqa
    url(r'^', include('util.urls', namespace='util')),
    url(r'^reports/', include('reports.urls', namespace='reports')),
    url(r'^hosts/', include('hosts.urls', namespace='hosts')),
    url(r'^packages/', include('packages.urls', namespace='packages')),
    url(r'^repos/', include('repos.urls', namespace='repos')),
    url(r'^os/', include('operatingsystems.urls', namespace='operatingsystems')),  # noqa
]

if settings.DEBUG:
    urlpatterns += [url(r'^static/(?P<path>.*)$', static.serve)]
