from django.conf.urls.defaults import *

urlpatterns = patterns('patchman.repos.views',

    url(r'^$', 'repo_list', name='repo_list' ),
    url(r'^(?P<repo>[-.\w]+)/$', 'repo_detail', name='repo_detail' ),

)
