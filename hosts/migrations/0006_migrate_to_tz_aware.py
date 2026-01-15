from django.db import migrations
from django.utils import timezone


def make_datetimes_tz_aware(apps, schema_editor):
    Host = apps.get_model('hosts', 'Host')
    for host in Host.objects.all():
        if host.lastreport and timezone.is_naive(host.lastreport):
            host.lastreport = timezone.make_aware(host.lastreport, timezone=timezone.get_default_timezone())
            host.save()
        if host.updated_at and timezone.is_naive(host.updated_at):
            host.updated_at = timezone.make_aware(host.updated_at, timezone=timezone.get_default_timezone())
            host.save()

class Migration(migrations.Migration):
    dependencies = [
        ('hosts', '0005_rename_os_host_osvariant'),
    ]

    operations = [
        migrations.RunPython(make_datetimes_tz_aware, migrations.RunPython.noop),
    ]
