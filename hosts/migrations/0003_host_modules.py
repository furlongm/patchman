# Generated by Django 3.2.19 on 2023-12-11 22:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0001_initial'),
        ('hosts', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='host',
            name='modules',
            field=models.ManyToManyField(blank=True, to='modules.Module'),
        ),
    ]