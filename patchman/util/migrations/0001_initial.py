# Generated manually for mTLS support

from django.db import migrations, models
import django.db.models.deletion
import patchman.util.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EnrollmentToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(default=patchman.util.models.generate_enrollment_token, max_length=64, unique=True)),
                ('hostname_pattern', models.CharField(blank=True, help_text='Glob pattern for allowed hostnames (e.g., "*.example.com"). Empty = any.', max_length=255)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('expires', models.DateTimeField()),
                ('single_use', models.BooleanField(default=True)),
                ('used_by', models.CharField(blank=True, max_length=255)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.CharField(blank=True, max_length=255)),
                ('notes', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='ClientCertificate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hostname', models.CharField(db_index=True, max_length=255)),
                ('serial_number', models.CharField(max_length=64, unique=True)),
                ('issued_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('revoked', models.BooleanField(default=False)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('revoked_reason', models.CharField(blank=True, max_length=255)),
                ('enrollment_token', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='certificates', to='util.enrollmenttoken')),
            ],
            options={
                'ordering': ['-issued_at'],
            },
        ),
    ]
