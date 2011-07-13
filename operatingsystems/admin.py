from django.contrib import admin
from patchman.operatingsystems.models import OS, OSGroup

admin.site.register(OS)
admin.site.register(OSGroup)

