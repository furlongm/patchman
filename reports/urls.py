from django.conf.urls.defaults import *

urlpatterns = patterns('patchman.reports.views',

    url(r'^upload/$', 'upload'),

)
