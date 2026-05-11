from django.db import migrations
from django.utils import timezone


def make_datetimes_tz_aware(apps, schema_editor):
    Report = apps.get_model('reports', 'Report')
    for report in Report.objects.all():
        if report.created and timezone.is_naive(report.created):
            report.created = timezone.make_aware(report.created, timezone=timezone.get_default_timezone())
            report.save()

class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0003_remove_report_accessed'),
    ]

    operations = [
        migrations.RunPython(make_datetimes_tz_aware, migrations.RunPython.noop),
    ]
