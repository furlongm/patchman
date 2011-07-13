from django.contrib import admin
from patchman.repos.models import Repository

class RepoAdmin(admin.ModelAdmin):
    readonly_fields = ('packages',)

admin.site.register(Repository, RepoAdmin)
