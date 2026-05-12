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
# along with  If not, see <http://www.gnu.org/licenses/>

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views import static
from rest_framework import routers

from patchman.arch import views as arch_views
from patchman.domains import views as domain_views
from patchman.errata import views as errata_views
from patchman.hosts import views as host_views
from patchman.operatingsystems import views as os_views
from patchman.packages import views as package_views
from patchman.reports import views as report_views
from patchman.repos import views as repo_views
from patchman.compliance import views as compliance_views
from patchman.security import views as security_views
from patchman.util.api import StatsView
from patchman.util.urls import cert_urlpatterns

router = routers.DefaultRouter()
router.register(r'package-architecture', arch_views.PackageArchitectureViewSet)
router.register(r'machine-architecture', arch_views.MachineArchitectureViewSet)
router.register(r'domain', domain_views.DomainViewSet)
router.register(r'host', host_views.HostViewSet)
router.register(r'host-repo', host_views.HostRepoViewSet)
router.register(r'os-variant', os_views.OSVariantViewSet)
router.register(r'os-release', os_views.OSReleaseViewSet)
router.register(r'package-name', package_views.PackageNameViewSet)
router.register(r'package', package_views.PackageViewSet)
router.register(r'package-update', package_views.PackageUpdateViewSet)
router.register(r'cve', security_views.CVEViewSet)
router.register(r'cwe', security_views.CWEViewSet)
router.register(r'reference', security_views.ReferenceViewSet)
router.register(r'erratum', errata_views.ErratumViewSet)
router.register(r'repo', repo_views.RepositoryViewSet)
router.register(r'mirror', repo_views.MirrorViewSet)
router.register(r'mirror-package', repo_views.MirrorPackageViewSet)
router.register(r'report', report_views.ReportViewSet, basename='report')
router.register(r'compliance-profile', compliance_views.ComplianceProfileViewSet)
router.register(r'compliance-rule', compliance_views.ComplianceRuleViewSet)
router.register(r'compliance-scan', compliance_views.ComplianceScanViewSet)

admin.autodiscover()

urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/stats/', StatsView.as_view(), name='api-stats'),
    path('api/compliance/stats/', compliance_views.ComplianceStatsView.as_view(), name='api-compliance-stats'),
    path('api/cert/', include(cert_urlpatterns)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),  # noqa
    path('select2/', include('django_select2.urls')),
    path('', include('patchman.util.urls', namespace='util')),
    path('errata/', include('patchman.errata.urls', namespace='errata')),
    path('reports/', include('patchman.reports.urls', namespace='reports')),
    path('hosts/', include('patchman.hosts.urls', namespace='hosts')),
    path('packages/', include('patchman.packages.urls', namespace='packages')),
    path('modules/', include('patchman.modules.urls', namespace='modules')),
    path('repos/', include('patchman.repos.urls', namespace='repos')),
    path('security/', include('patchman.security.urls', namespace='security')),
    path('compliance/', include('patchman.compliance.urls', namespace='compliance')),
    path('os/', include('patchman.operatingsystems.urls', namespace='operatingsystems')),  # noqa
]

if settings.DEBUG:
    urlpatterns += [path('static/<str:path>', static.serve)]
