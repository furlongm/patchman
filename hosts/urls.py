from django.conf.urls.defaults import *

urlpatterns = patterns('patchman.hosts.views',

    url(r'^$', 'host_list', name='host_list' ),
    url(r'^(?P<hostname>[-.\w]+)/$', 'host_detail', name='host_detail' ),
    url(r'^(?P<hostname>[-.\w]+)/delete/$', 'host_delete', name='host_delete' ),

)
