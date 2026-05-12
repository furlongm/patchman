from django.db import migrations, models


class Migration(migrations.Migration):

   dependencies = [
       ('reports', '0006_alter_report_options'),
   ]

   operations = [
       migrations.AddField(
           model_name='report',
           name='compliance',
           field=models.TextField(blank=True, null=True),
       ),
   ]
