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

from django.test import TestCase, override_settings

from operatingsystems.models import OSRelease, OSVariant


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class OSReleaseMethodTests(TestCase):
    """Tests for OSRelease model methods."""

    def test_osrelease_creation(self):
        """Test creating an OSRelease."""
        release = OSRelease.objects.create(name='Ubuntu 22.04')
        self.assertEqual(release.name, 'Ubuntu 22.04')

    def test_osrelease_str(self):
        """Test OSRelease __str__ method."""
        release = OSRelease.objects.create(name='Ubuntu 22.04')
        self.assertEqual(str(release), 'Ubuntu 22.04')

    def test_osrelease_get_absolute_url(self):
        """Test OSRelease.get_absolute_url()."""
        release = OSRelease.objects.create(name='Rocky Linux 9')
        url = release.get_absolute_url()
        self.assertIn(str(release.id), url)

    def test_osrelease_unique_name(self):
        """Test OSRelease name is unique."""
        OSRelease.objects.create(name='Ubuntu 22.04')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            OSRelease.objects.create(name='Ubuntu 22.04')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class OSVariantMethodTests(TestCase):
    """Tests for OSVariant model methods."""

    def setUp(self):
        """Set up test data."""
        self.release = OSRelease.objects.create(name='Ubuntu 22.04')

    def test_osvariant_creation(self):
        """Test creating an OSVariant."""
        variant = OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS',
            osrelease=self.release,
        )
        self.assertEqual(variant.name, 'Ubuntu 22.04.3 LTS')
        self.assertEqual(variant.osrelease, self.release)

    def test_osvariant_str(self):
        """Test OSVariant __str__ method."""
        variant = OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS',
            osrelease=self.release,
        )
        # __str__ returns 'name arch' format
        self.assertIn('Ubuntu 22.04.3 LTS', str(variant))

    def test_osvariant_get_absolute_url(self):
        """Test OSVariant.get_absolute_url()."""
        variant = OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS',
            osrelease=self.release,
        )
        url = variant.get_absolute_url()
        self.assertIn(str(variant.id), url)

    def test_osvariant_unique_name(self):
        """Test OSVariant name is unique."""
        OSVariant.objects.create(
            name='Ubuntu 22.04.3 LTS',
            osrelease=self.release,
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            OSVariant.objects.create(
                name='Ubuntu 22.04.3 LTS',
                osrelease=self.release,
            )
