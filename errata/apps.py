# Copyright 2025 Marcus Furlong <furlongm@gmail.com>
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

from django.apps import AppConfig


class ErrataConfig(AppConfig):
    name = 'errata'

    def ready(self):
        from datetime import timedelta

        from django.db.models.signals import post_save
        from django.utils import timezone

        def set_initial_last_run(sender, instance, created, **kwargs):
            if created and instance.name == 'update_errata_cves_cwes_every_12_hours':
                instance.last_run_at = timezone.now() - timedelta(days=1)
                instance.save(update_fields=['last_run_at'])

        from django_celery_beat.models import PeriodicTask
        post_save.connect(set_initial_last_run, sender=PeriodicTask)
