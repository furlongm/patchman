# Generated by Django 3.2.23 on 2024-02-04 22:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0002_auto_20240204_2214'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='module',
            options={'ordering': ('name', 'stream'), 'verbose_name': 'Module', 'verbose_name_plural': 'Modules'},
        ),
    ]
