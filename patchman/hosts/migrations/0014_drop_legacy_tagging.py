from django.db import migrations

LEGACY_TAGGING_TABLES = ['tagging_taggeditem', 'tagging_tag']


def drop_legacy_tagging(apps, schema_editor):
    # 0004 never dropped the django-tagging column/tables on 3.x upgrades
    conn = schema_editor.connection
    q = schema_editor.quote_name
    with conn.cursor() as cursor:
        columns = [c.name for c in conn.introspection.get_table_description(cursor, 'hosts_host')]
        tables = conn.introspection.table_names(cursor)

    if 'tags' in columns:
        if getattr(conn.features, 'can_alter_table_drop_column', True):
            schema_editor.execute(f'ALTER TABLE {q("hosts_host")} DROP COLUMN {q("tags")}')
        else:
            # old sqlite: rebuilding the table from the model drops unknown columns
            schema_editor._remake_table(apps.get_model('hosts', 'Host'))

    for table in LEGACY_TAGGING_TABLES:
        if table in tables:
            schema_editor.execute(f'DROP TABLE {q(table)}')


class Migration(migrations.Migration):

    dependencies = [
        ('hosts', '0013_alter_hostrepo_unique_together_and_more'),
    ]

    operations = [
        migrations.RunPython(drop_legacy_tagging, migrations.RunPython.noop),
    ]
