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

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from hosts.models import Host


@receiver(pre_save, sender=Host)
def track_osvariant_change(sender, instance, **kwargs):
    """Track old osvariant before save to update its count."""
    if instance.pk:
        try:
            old_instance = Host.objects.get(pk=instance.pk)
            instance._old_osvariant = old_instance.osvariant
        except Host.DoesNotExist:
            instance._old_osvariant = None
    else:
        instance._old_osvariant = None


@receiver(post_save, sender=Host)
def update_osvariant_count_on_save(sender, instance, created, **kwargs):
    """Update OSVariant.hosts_count when Host is created or osvariant changes."""
    # Update new osvariant count
    if instance.osvariant:
        instance.osvariant.hosts_count = Host.objects.filter(osvariant=instance.osvariant).count()
        instance.osvariant.save(update_fields=['hosts_count'])

    # Update old osvariant count if it changed
    old_osvariant = getattr(instance, '_old_osvariant', None)
    if old_osvariant and old_osvariant != instance.osvariant:
        old_osvariant.hosts_count = Host.objects.filter(osvariant=old_osvariant).count()
        old_osvariant.save(update_fields=['hosts_count'])


@receiver(post_delete, sender=Host)
def update_osvariant_count_on_delete(sender, instance, **kwargs):
    """Update OSVariant.hosts_count when Host is deleted."""
    if instance.osvariant:
        instance.osvariant.hosts_count = Host.objects.filter(osvariant=instance.osvariant).count()
        instance.osvariant.save(update_fields=['hosts_count'])
