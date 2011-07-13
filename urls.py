from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    url(r'^dashboard/$', 'patchman.views.dashboard', name='dashboard'),
    url(r'^reports/', include('patchman.reports.urls')),
    url(r'^hosts/', include('patchman.hosts.urls')),
    url(r'^packages/', include('patchman.packages.urls')),
    url(r'^repos/', include('patchman.repos.urls')),
    url(r'^os/', include('patchman.operatingsystems.urls')),
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', name='login'),     
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', name='logout'),
    # Uncomment the admin/doc line below to enable admin documentation:
    #(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )
