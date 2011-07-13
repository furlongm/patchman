from django.contrib import admin
from patchman.packages.models import Package,PackageName

admin.site.register(Package)
admin.site.register(PackageName)
