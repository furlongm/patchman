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

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from arch.models import MachineArchitecture, PackageArchitecture
from domains.models import Domain
from hosts.models import Host
from operatingsystems.models import OSRelease, OSVariant


@override_settings(
    DEFAULT_FILE_STORAGE='django.core.files.storage.InMemoryStorage',
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class StatsAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass',
        )
        self.client.login(username='testuser', password='testpass')

        self.domain = Domain.objects.create(name='example.com')
        self.m_arch = MachineArchitecture.objects.create(name='x86_64')
        self.p_arch = PackageArchitecture.objects.create(name='x86_64')
        self.osrelease = OSRelease.objects.create(name='TestOS 1')

    def _create_variant(self, variant_name):
        return OSVariant.objects.create(
            name=variant_name, osrelease=self.osrelease,
        )

    def _create_host(self, hostname, osvariant, **kwargs):
        defaults = {
            'ipaddress': '192.168.1.1',
            'reversedns': hostname,
            'domain': self.domain,
            'arch': self.m_arch,
            'osvariant': osvariant,
            'lastreport': timezone.now(),
        }
        defaults.update(kwargs)
        return Host.objects.create(hostname=hostname, **defaults)

    def test_stats_requires_auth(self):
        self.client.logout()
        response = self.client.get('/api/stats/')
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_stats_returns_all_sections(self):
        response = self.client.get('/api/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('host_status', data)
        self.assertIn('os_distribution', data)
        self.assertIn('kernel_distribution', data)
        self.assertIn('updates_by_os', data)

    def test_host_status_counts(self):
        v = self._create_variant('Ubuntu 24.04')
        self._create_host('patched.example.com', v)
        self._create_host(
            'sec.example.com', v, sec_updates_count=3,
        )
        self._create_host(
            'bug.example.com', v, bug_updates_count=2,
        )
        self._create_host(
            'reboot.example.com', v, reboot_required=True,
        )
        self._create_host(
            'stale.example.com', v,
            lastreport=timezone.now() - timedelta(days=30),
        )

        response = self.client.get('/api/stats/')
        hs = response.json()['host_status']
        self.assertEqual(hs['total'], 5)
        self.assertEqual(hs['security_pending'], 1)
        self.assertEqual(hs['bugfix_pending'], 1)
        self.assertEqual(hs['reboot_required'], 1)
        self.assertEqual(hs['stale'], 1)
        # patched = total - sec - bug = 5 - 1 - 1 = 3
        self.assertEqual(hs['patched'], 3)

    def test_os_distribution(self):
        v1 = self._create_variant('Debian 12')
        v2 = self._create_variant('RHEL 9')
        self._create_host('deb1.example.com', v1)
        self._create_host('deb2.example.com', v1)
        self._create_host('rhel1.example.com', v2)
        # refresh cached hosts_count
        v1.refresh_from_db()
        v2.refresh_from_db()

        response = self.client.get('/api/stats/')
        os_dist = response.json()['os_distribution']
        self.assertIn('Debian 12', os_dist['labels'])
        self.assertIn('RHEL 9', os_dist['labels'])

    def test_kernel_distribution(self):
        v = self._create_variant('Debian 12')
        self._create_host(
            'h1.example.com', v, kernel='6.1.0-18-amd64',
        )
        self._create_host(
            'h2.example.com', v, kernel='6.1.0-18-amd64',
        )
        self._create_host(
            'h3.example.com', v, kernel='6.1.0-20-amd64',
        )

        response = self.client.get('/api/stats/')
        kd = response.json()['kernel_distribution']
        self.assertIn('6.1.0-18-amd64', kd['labels'])
        self.assertIn('6.1.0-20-amd64', kd['labels'])
        # 6.1.0-18 should have count 2
        idx = kd['labels'].index('6.1.0-18-amd64')
        self.assertEqual(kd['values'][idx], 2)

    def test_updates_by_os(self):
        v1 = self._create_variant('Ubuntu 24.04')
        v2 = self._create_variant('AlmaLinux 9')
        self._create_host(
            'u1.example.com', v1, sec_updates_count=5,
        )
        self._create_host(
            'a1.example.com', v2, bug_updates_count=3,
        )

        response = self.client.get('/api/stats/')
        uo = response.json()['updates_by_os']
        self.assertIn('Ubuntu 24.04', uo['labels'])
        self.assertIn('AlmaLinux 9', uo['labels'])

    def test_empty_database(self):
        response = self.client.get('/api/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['host_status']['total'], 0)
        self.assertEqual(data['host_status']['patched'], 0)
        self.assertEqual(data['os_distribution']['labels'], [])
        self.assertEqual(data['kernel_distribution']['labels'], [])
        self.assertEqual(data['updates_by_os']['labels'], [])
        self.assertEqual(data['stale_histogram']['labels'][0], '< 1 day')
        self.assertEqual(data['reboot_by_os']['labels'], [])
        self.assertEqual(data['top_hosts']['labels'], [])
        self.assertEqual(data['top_errata']['labels'], [])
        self.assertEqual(data['mirror_health']['total'], 0)
        self.assertEqual(data['errata_age']['labels'][0], '< 1 week')

    def test_os_distribution_top_n_grouping(self):
        """When >10 OS variants exist, extras are grouped as 'Other'."""
        variants = []
        for i in range(12):
            v = self._create_variant(f'Distro {i}')
            self._create_host(f'h{i}.example.com', v)
            variants.append(v)
        # add extra host to first variant so it sorts higher
        self._create_host('extra.example.com', variants[0])

        response = self.client.get('/api/stats/')
        os_dist = response.json()['os_distribution']
        # 10 named + 'Other'
        self.assertEqual(len(os_dist['labels']), 11)
        self.assertEqual(os_dist['labels'][-1], 'Other')

    def test_stale_histogram(self):
        v = self._create_variant('Debian 12')
        self._create_host('fresh.example.com', v)
        self._create_host(
            'old.example.com', v,
            lastreport=timezone.now() - timedelta(days=10),
        )
        self._create_host(
            'ancient.example.com', v,
            lastreport=timezone.now() - timedelta(days=60),
        )

        response = self.client.get('/api/stats/')
        sh = response.json()['stale_histogram']
        self.assertEqual(len(sh['labels']), 6)
        self.assertEqual(sh['labels'][0], '< 1 day')
        self.assertEqual(sh['labels'][-1], '> 4 weeks')
        # total across all buckets should equal total hosts
        self.assertEqual(sum(sh['values']), 3)

    def test_reboot_by_os(self):
        v1 = self._create_variant('Ubuntu 24.04')
        v2 = self._create_variant('RHEL 9')
        self._create_host('u1.example.com', v1, reboot_required=True)
        self._create_host('u2.example.com', v1, reboot_required=True)
        self._create_host('r1.example.com', v2)

        response = self.client.get('/api/stats/')
        rb = response.json()['reboot_by_os']
        self.assertIn('Ubuntu 24.04', rb['labels'])
        self.assertNotIn('RHEL 9', rb['labels'])
        idx = rb['labels'].index('Ubuntu 24.04')
        self.assertEqual(rb['values'][idx], 2)

    def test_top_hosts_by_updates(self):
        v = self._create_variant('Debian 12')
        self._create_host(
            'bad.example.com', v,
            sec_updates_count=10, bug_updates_count=5,
        )
        self._create_host(
            'ok.example.com', v,
            sec_updates_count=1,
        )
        self._create_host('good.example.com', v)

        response = self.client.get('/api/stats/')
        th = response.json()['top_hosts']
        self.assertEqual(th['labels'][0], 'bad.example.com')
        self.assertEqual(th['security'][0], 10)
        self.assertEqual(th['bugfix'][0], 5)
        # good host (0 updates) should not appear
        self.assertNotIn('good.example.com', th['labels'])

    def test_top_security_errata(self):
        from errata.models import Erratum
        now = timezone.now()
        v = self._create_variant('Debian 12')
        h1 = self._create_host('h1.example.com', v)
        h2 = self._create_host('h2.example.com', v)
        h3 = self._create_host('h3.example.com', v)
        e1 = Erratum.objects.create(
            name='DSA-5000-1', e_type='security',
            issue_date=now, synopsis='test',
        )
        e2 = Erratum.objects.create(
            name='DSA-5001-1', e_type='security',
            issue_date=now, synopsis='test',
        )
        e_bug = Erratum.objects.create(
            name='DLA-5000-1', e_type='bugfix',
            issue_date=now, synopsis='test',
        )
        h1.errata.add(e1, e2)
        h2.errata.add(e1)
        h3.errata.add(e_bug)

        response = self.client.get('/api/stats/')
        te = response.json()['top_errata']
        # e1 affects 2 hosts, e2 affects 1, bugfix shouldn't appear
        self.assertEqual(te['labels'][0], 'DSA-5000-1')
        self.assertEqual(te['values'][0], 2)
        self.assertNotIn('DLA-5000-1', te['labels'])

    def test_mirror_health(self):
        from repos.models import Mirror, Repository
        repo = Repository.objects.create(
            name='test-repo', arch=self.m_arch, repotype='deb',
        )
        Mirror.objects.create(
            repo=repo, url='http://m1.example.com/',
            enabled=True, last_access_ok=True,
        )
        Mirror.objects.create(
            repo=repo, url='http://m2.example.com/',
            enabled=True, last_access_ok=False,
        )
        Mirror.objects.create(
            repo=repo, url='http://m3.example.com/',
            enabled=False, last_access_ok=True,
        )

        response = self.client.get('/api/stats/')
        mh = response.json()['mirror_health']
        self.assertEqual(mh['total'], 3)
        self.assertEqual(mh['values'][0], 1)  # OK
        self.assertEqual(mh['values'][1], 1)  # Failing
        self.assertEqual(mh['values'][2], 1)  # Disabled

    def test_errata_age_histogram(self):
        from errata.models import Erratum
        now = timezone.now()
        v = self._create_variant('Debian 12')
        h1 = self._create_host('h1.example.com', v)
        # recent erratum (< 1 week)
        e_new = Erratum.objects.create(
            name='DSA-6000-1', e_type='security',
            issue_date=now - timedelta(days=2), synopsis='new',
        )
        # old erratum (> 6 months)
        e_old = Erratum.objects.create(
            name='DSA-1000-1', e_type='security',
            issue_date=now - timedelta(days=200), synopsis='old',
        )
        # erratum not on any host — should not be counted
        Erratum.objects.create(
            name='DSA-9999-1', e_type='security',
            issue_date=now - timedelta(days=100), synopsis='orphan',
        )
        h1.errata.add(e_new, e_old)

        response = self.client.get('/api/stats/')
        ea = response.json()['errata_age']
        self.assertEqual(len(ea['labels']), 5)
        self.assertEqual(ea['labels'][0], '< 1 week')
        self.assertEqual(ea['labels'][-1], '> 6 months')
        # total across buckets should be 2 (only host-attached errata)
        self.assertEqual(sum(ea['values']), 2)
