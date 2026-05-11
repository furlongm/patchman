# Copyright 2026 Marcus Furlong <furlongm@gmail.com>
#
# This file is part of Patchman.
#
# Patchman is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 only.
#
# Patchman is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchman. If not, see <http://www.gnu.org/licenses/>

from django.db import migrations


def backfill_counts(apps, schema_editor):
    Erratum = apps.get_model('errata', 'Erratum')
    for erratum in Erratum.objects.all().iterator():
        erratum.affected_packages_count = erratum.affected_packages.count()
        erratum.fixed_packages_count = erratum.fixed_packages.count()
        erratum.osreleases_count = erratum.osreleases.count()
        erratum.cves_count = erratum.cves.count()
        erratum.references_count = erratum.references.count()
        erratum.save(update_fields=[
            'affected_packages_count',
            'fixed_packages_count',
            'osreleases_count',
            'cves_count',
            'references_count',
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('errata', '0008_add_cached_count_fields'),
    ]

    operations = [
        migrations.RunPython(backfill_counts, migrations.RunPython.noop),
    ]
