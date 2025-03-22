from django.db import migrations
from django.utils import timezone

def make_datetimes_tz_aware(apps, schema_editor):
    Mirror = apps.get_model('repos', 'Mirror')
    for mirror in Mirror.objects.all():
        if mirror.timestamp and timezone.is_naive(mirror.timestamp):
            mirror.timestamp = timezone.make_aware(mirror.timestamp, timezone=timezone.get_default_timezone())
            mirror.save()

class Migration(migrations.Migration):
    dependencies = [
        ('repos', '0002_alter_repository_repotype'),
    ]

    operations = [
        migrations.RunPython(make_datetimes_tz_aware, migrations.RunPython.noop),
    ]
