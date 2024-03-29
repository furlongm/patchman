# Generated by Django 3.2.23 on 2024-02-04 22:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('arch', '0001_initial'),
        ('modules', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='module',
            name='context',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='module',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='module',
            name='stream',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterUniqueTogether(
            name='module',
            unique_together={('name', 'stream', 'version', 'context', 'arch')},
        ),
    ]
