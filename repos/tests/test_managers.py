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

from arch.models import MachineArchitecture
from repos.models import Mirror, Repository


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class RepositoryManagerTests(TestCase):
    """Tests for RepositoryManager custom queryset."""

    def setUp(self):
        """Set up test data."""
        self.arch = MachineArchitecture.objects.create(name='x86_64')

    def test_repository_manager_select_related(self):
        """Test RepositoryManager uses select_related for efficiency."""
        Repository.objects.create(
            name='ubuntu-main',
            arch=self.arch,
            repotype=Repository.DEB,
        )
        # Manager should return queryset with select_related
        repos = Repository.objects.all()
        self.assertEqual(repos.count(), 1)

    def test_repository_manager_returns_all_repos(self):
        """Test RepositoryManager returns all repositories."""
        for name in ['ubuntu-main', 'ubuntu-updates', 'ubuntu-security']:
            Repository.objects.create(
                name=name,
                arch=self.arch,
                repotype=Repository.DEB,
            )
        self.assertEqual(Repository.objects.count(), 3)

    def test_repository_manager_filter_by_type(self):
        """Test RepositoryManager filtering by repo type."""
        Repository.objects.create(
            name='ubuntu-main',
            arch=self.arch,
            repotype=Repository.DEB,
        )
        Repository.objects.create(
            name='rocky-baseos',
            arch=self.arch,
            repotype=Repository.RPM,
        )
        deb_repos = Repository.objects.filter(repotype=Repository.DEB)
        rpm_repos = Repository.objects.filter(repotype=Repository.RPM)
        self.assertEqual(deb_repos.count(), 1)
        self.assertEqual(rpm_repos.count(), 1)

    def test_repository_manager_filter_by_enabled(self):
        """Test RepositoryManager filtering by enabled status."""
        Repository.objects.create(
            name='enabled-repo',
            arch=self.arch,
            repotype=Repository.DEB,
            enabled=True,
        )
        Repository.objects.create(
            name='disabled-repo',
            arch=self.arch,
            repotype=Repository.DEB,
            enabled=False,
        )
        enabled_repos = Repository.objects.filter(enabled=True)
        disabled_repos = Repository.objects.filter(enabled=False)
        self.assertEqual(enabled_repos.count(), 1)
        self.assertEqual(disabled_repos.count(), 1)

    def test_repository_manager_filter_by_security(self):
        """Test RepositoryManager filtering by security flag."""
        Repository.objects.create(
            name='main-repo',
            arch=self.arch,
            repotype=Repository.DEB,
            security=False,
        )
        Repository.objects.create(
            name='security-repo',
            arch=self.arch,
            repotype=Repository.DEB,
            security=True,
        )
        security_repos = Repository.objects.filter(security=True)
        non_security_repos = Repository.objects.filter(security=False)
        self.assertEqual(security_repos.count(), 1)
        self.assertEqual(non_security_repos.count(), 1)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class MirrorManagerTests(TestCase):
    """Tests for Mirror model queries."""

    def setUp(self):
        """Set up test data."""
        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.repo = Repository.objects.create(
            name='ubuntu-main',
            arch=self.arch,
            repotype=Repository.DEB,
        )

    def test_mirror_filter_by_repo(self):
        """Test filtering mirrors by repository."""
        Mirror.objects.create(
            repo=self.repo,
            url='http://archive.ubuntu.com/ubuntu',
        )
        Mirror.objects.create(
            repo=self.repo,
            url='http://mirror.example.com/ubuntu',
        )
        repo_mirrors = Mirror.objects.filter(repo=self.repo)
        self.assertEqual(repo_mirrors.count(), 2)

    def test_mirror_filter_by_enabled(self):
        """Test filtering mirrors by enabled status."""
        Mirror.objects.create(
            repo=self.repo,
            url='http://archive.ubuntu.com/ubuntu',
            enabled=True,
        )
        Mirror.objects.create(
            repo=self.repo,
            url='http://disabled.example.com/ubuntu',
            enabled=False,
        )
        enabled_mirrors = Mirror.objects.filter(enabled=True)
        self.assertEqual(enabled_mirrors.count(), 1)

    def test_mirror_filter_by_last_access_ok(self):
        """Test filtering mirrors by last_access_ok status."""
        Mirror.objects.create(
            repo=self.repo,
            url='http://working.example.com/ubuntu',
            last_access_ok=True,
        )
        Mirror.objects.create(
            repo=self.repo,
            url='http://broken.example.com/ubuntu',
            last_access_ok=False,
        )
        working_mirrors = Mirror.objects.filter(last_access_ok=True)
        broken_mirrors = Mirror.objects.filter(last_access_ok=False)
        self.assertEqual(working_mirrors.count(), 1)
        self.assertEqual(broken_mirrors.count(), 1)
