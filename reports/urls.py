from django.conf.urls.defaults import *

urlpatterns = patterns('patchman.reports.views',

    url(r'^$', 'report_list', name='report_list' ),
    url(r'^(?P<report>[-.\w]+)/$', 'report_detail', name='report_detail' ),
    url(r'^upload/$', 'upload'),
)
