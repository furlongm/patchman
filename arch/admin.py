from django.contrib import admin
from patchman.arch.models import PackageArchitecture,MachineArchitecture

admin.site.register(PackageArchitecture)
admin.site.register(MachineArchitecture)
