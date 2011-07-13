from django.conf.urls.defaults import *

urlpatterns = patterns('patchman.operatingsystems.views',

    url(r'^$', 'os_list', name='os_list' ),
    url(r'^groups/$', 'osgroup_list', name= 'osgroup_list'),
    url(r'^(?P<os_id>[-.\w]+)/$', 'os_detail', name='os_detail' ),
    url(r'^groups/(?P<osgroup_id>[-.\w]+)/$', 'osgroup_detail', name='osgroup_detail' ),
)
