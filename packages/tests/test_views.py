from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from arch.models import PackageArchitecture
from packages.models import Package, PackageName, PackageUpdate


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class PackageUpdateViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass'
        )
        self.client.login(username='testuser', password='testpass')
        self.arch = PackageArchitecture.objects.create(name='x86_64')
        self.name = PackageName.objects.create(name='openssl')
        self.old = Package.objects.create(
            name=self.name, arch=self.arch, epoch='',
            version='1.1.1', release='1', packagetype='R',
        )
        self.new = Package.objects.create(
            name=self.name, arch=self.arch, epoch='',
            version='1.1.2', release='1', packagetype='R',
        )
        self.sec_update = PackageUpdate.objects.create(
            oldpackage=self.old, newpackage=self.new, security=True,
        )
        self.bug_update = PackageUpdate.objects.create(
            oldpackage=self.old, newpackage=self.new, security=False,
        )

    def test_update_list(self):
        resp = self.client.get(reverse('packages:package_update_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'openssl')

    def test_update_list_filter_security(self):
        resp = self.client.get(
            reverse('packages:package_update_list'), {'security': 'true'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Security')

    def test_update_list_filter_bugfix(self):
        resp = self.client.get(
            reverse('packages:package_update_list'), {'security': 'false'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Bugfix')

    def test_update_list_search(self):
        resp = self.client.get(
            reverse('packages:package_update_list'), {'search': 'openssl'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'openssl')

    def test_update_list_search_no_results(self):
        resp = self.client.get(
            reverse('packages:package_update_list'), {'search': 'nonexistent'}
        )
        self.assertEqual(resp.status_code, 200)

    def test_update_list_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse('packages:package_update_list'))
        self.assertEqual(resp.status_code, 302)
