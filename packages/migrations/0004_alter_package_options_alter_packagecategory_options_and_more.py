# Generated by Django 4.2.19 on 2025-03-04 22:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('packages', '0003_auto_20250207_1746'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='package',
            options={'ordering': ['name', 'epoch', 'version', 'release', 'arch']},
        ),
        migrations.AlterModelOptions(
            name='packagecategory',
            options={'ordering': ['name'], 'verbose_name': 'Package Category', 'verbose_name_plural': 'Package Categories'},
        ),
        migrations.AlterModelOptions(
            name='packagename',
            options={'ordering': ['name'], 'verbose_name': 'Package', 'verbose_name_plural': 'Packages'},
        ),
    ]
