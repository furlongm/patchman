from django.conf.urls.defaults import *

urlpatterns = patterns('patchman.packages.views',

    url(r'^$', 'package_list', name='package_list' ),
    url(r'^(?P<packagename>[-.\w]+)/$', 'package_detail', name='package_detail' ),

)
