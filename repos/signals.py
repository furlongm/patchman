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

from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from repos.models import Mirror


@receiver(m2m_changed, sender=Mirror.packages.through)
def update_mirror_packages_count(sender, instance, action, **kwargs):
    """Update packages_count when Mirror.packages M2M changes."""
    if action in ('post_add', 'post_remove', 'post_clear'):
        instance.packages_count = instance.packages.count()
        instance.save(update_fields=['packages_count'])
