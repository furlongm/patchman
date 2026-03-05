from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from arch.models import MachineArchitecture
from repos.models import Mirror, Repository


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class RepoBulkActionTests(TestCase):
    """Tests for repo_bulk_action view."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass'
        )
        self.client.login(username='testuser', password='testpass')
        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.repos = []
        for i in range(3):
            self.repos.append(Repository.objects.create(
                name=f'repo-{i}',
                arch=self.arch,
                repotype='D',
                enabled=True,
            ))

    def test_bulk_delete_selected(self):
        """Test bulk delete with individually selected repos."""
        ids = [str(r.id) for r in self.repos[:2]]
        resp = self.client.post(reverse('repos:repo_bulk_action'), {
            'action': 'delete',
            'selected_ids': ids,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Repository.objects.count(), 1)

    def test_bulk_delete_select_all_filtered(self):
        """Test bulk delete with select-all-filtered (uses .distinct())."""
        resp = self.client.post(reverse('repos:repo_bulk_action'), {
            'action': 'delete',
            'select_all_filtered': '1',
            'filter_params': '',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Repository.objects.count(), 0)

    def test_bulk_enable_disable(self):
        """Test bulk enable/disable actions."""
        ids = [str(r.id) for r in self.repos]
        self.client.post(reverse('repos:repo_bulk_action'), {
            'action': 'disable',
            'selected_ids': ids,
        })
        self.assertTrue(all(
            not r.enabled for r in Repository.objects.all()
        ))
        self.client.post(reverse('repos:repo_bulk_action'), {
            'action': 'enable',
            'selected_ids': ids,
        })
        self.assertTrue(all(
            r.enabled for r in Repository.objects.all()
        ))


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class MirrorBulkActionTests(TestCase):
    """Tests for mirror_bulk_action view."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass'
        )
        self.client.login(username='testuser', password='testpass')
        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.repo = Repository.objects.create(
            name='repo-0',
            arch=self.arch,
            repotype='D',
            enabled=True,
        )
        self.mirrors = []
        for i in range(3):
            self.mirrors.append(Mirror.objects.create(
                repo=self.repo,
                url=f'http://mirror{i}.example.com/repo',
            ))

    def test_bulk_delete_select_all_filtered(self):
        """Test bulk delete mirrors with select-all-filtered (uses .distinct())."""
        resp = self.client.post(reverse('repos:mirror_bulk_action'), {
            'action': 'delete',
            'select_all_filtered': '1',
            'filter_params': '',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Mirror.objects.count(), 0)

    def test_bulk_delete_selected(self):
        """Test bulk delete with individually selected mirrors."""
        ids = [str(m.id) for m in self.mirrors[:2]]
        resp = self.client.post(reverse('repos:mirror_bulk_action'), {
            'action': 'delete',
            'selected_ids': ids,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Mirror.objects.count(), 1)
