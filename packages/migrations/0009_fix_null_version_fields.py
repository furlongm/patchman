from django.db import migrations


def fix_null_version_fields(apps, schema_editor):
    Package = apps.get_model('packages', 'Package')
    Package.objects.filter(epoch__isnull=True).update(epoch='')
    Package.objects.filter(version__isnull=True).update(version='')
    Package.objects.filter(release__isnull=True).update(release='')


class Migration(migrations.Migration):

    dependencies = [
        ('packages', '0008_alter_package_unique_together_and_more'),
    ]

    operations = [
        migrations.RunPython(
            fix_null_version_fields,
            migrations.RunPython.noop,
        ),
    ]
