# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('packages', '0002_auto_20160709_1813'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='erratum',
            options={'verbose_name': 'Erratum', 'verbose_name_plural': 'Errata'},
        ),
    ]
