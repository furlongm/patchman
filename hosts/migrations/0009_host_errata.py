# Generated by Django 4.2.19 on 2025-03-10 19:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('errata', '0006_alter_erratum_options'),
        ('hosts', '0008_alter_host_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='host',
            name='errata',
            field=models.ManyToManyField(blank=True, to='errata.erratum'),
        ),
    ]
