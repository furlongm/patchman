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

from errata.models import Erratum


@receiver(m2m_changed, sender=Erratum.affected_packages.through)
def update_affected_packages_count(sender, instance, action, **kwargs):
    """Update affected_packages_count when Erratum.affected_packages M2M changes."""
    if action in ('post_add', 'post_remove', 'post_clear'):
        instance.affected_packages_count = instance.affected_packages.count()
        instance.save(update_fields=['affected_packages_count'])


@receiver(m2m_changed, sender=Erratum.fixed_packages.through)
def update_fixed_packages_count(sender, instance, action, **kwargs):
    """Update fixed_packages_count when Erratum.fixed_packages M2M changes."""
    if action in ('post_add', 'post_remove', 'post_clear'):
        instance.fixed_packages_count = instance.fixed_packages.count()
        instance.save(update_fields=['fixed_packages_count'])


@receiver(m2m_changed, sender=Erratum.osreleases.through)
def update_osreleases_count(sender, instance, action, **kwargs):
    """Update osreleases_count when Erratum.osreleases M2M changes."""
    if action in ('post_add', 'post_remove', 'post_clear'):
        instance.osreleases_count = instance.osreleases.count()
        instance.save(update_fields=['osreleases_count'])


@receiver(m2m_changed, sender=Erratum.cves.through)
def update_cves_count(sender, instance, action, **kwargs):
    """Update cves_count when Erratum.cves M2M changes."""
    if action in ('post_add', 'post_remove', 'post_clear'):
        instance.cves_count = instance.cves.count()
        instance.save(update_fields=['cves_count'])


@receiver(m2m_changed, sender=Erratum.references.through)
def update_references_count(sender, instance, action, **kwargs):
    """Update references_count when Erratum.references M2M changes."""
    if action in ('post_add', 'post_remove', 'post_clear'):
        instance.references_count = instance.references.count()
        instance.save(update_fields=['references_count'])
