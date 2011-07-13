from django.contrib import admin
from patchman.hosts.models import Host 

class HostAdmin(admin.ModelAdmin):
    readonly_fields = ('packages', 'updates')

admin.site.register(Host, HostAdmin)


