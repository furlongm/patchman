# Generated by Django 4.2.18 on 2025-02-08 20:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('repos', '0001_initial'),
        ('hosts', '0005_rename_os_host_osvariant'),
        ('operatingsystems', '0004_alter_osgroup_unique_together'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='OSGroup',
            new_name='OSRelease',
        ),
        migrations.RenameModel(
            old_name='OS',
            new_name='OSVariant',
        ),
        migrations.AlterModelOptions(
            name='osrelease',
            options={'ordering': ('name',), 'verbose_name': 'Operating System Release', 'verbose_name_plural': 'Operating System Releases'},
        ),
        migrations.AlterModelOptions(
            name='osvariant',
            options={'ordering': ('name',), 'verbose_name': 'Operating System Variant', 'verbose_name_plural': 'Operating System Variants'},
        ),
        migrations.RenameField(
            model_name='osvariant',
            old_name='osgroup',
            new_name='osrelease',
        ),
    ]
