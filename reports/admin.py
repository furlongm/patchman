from django.contrib import admin
from patchman.reports.models import Report

class ReportAdmin(admin.ModelAdmin):
    readonly_fields = ('packages',)

admin.site.register(Report, ReportAdmin)
