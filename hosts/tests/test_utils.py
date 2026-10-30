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

from unittest.mock import patch

from django.test import TestCase

from arch.models import MachineArchitecture
from domains.models import Domain
from hosts.utils import get_or_create_host
from operatingsystems.models import OSRelease, OSVariant
from reports.models import Report


@patch('hosts.models.Host.check_rdns')
class GetOrCreateHostTagTests(TestCase):

    def setUp(self):
        self.arch = MachineArchitecture.objects.create(name='x86_64')
        self.domain = Domain.objects.create(name='example.com')
        self.osvariant = OSVariant.objects.create(
            name='Debian 13', osrelease=OSRelease.objects.create(name='Debian 13'),
        )

    def host_tags(self, protocol, tags):
        report = Report.objects.create(
            host='tags.example.com', report_ip='192.168.1.10', os='Debian 13',
            kernel='6.12.57+deb13-amd64', arch='x86_64', protocol=protocol, tags=tags,
        )
        host = get_or_create_host(report, self.arch, self.osvariant, self.domain)
        return sorted(host.tags.names())

    def test_protocol1_space_delimited(self, _):
        self.assertEqual(self.host_tags('1', 'web prod'), ['prod', 'web'])

    def test_protocol1_comma_delimited(self, _):
        self.assertEqual(self.host_tags('1', 'web, prod'), ['prod', 'web'])

    def test_protocol2_keeps_spaces_within_tags(self, _):
        self.assertEqual(self.host_tags('2', 'my tag, web'), ['my tag', 'web'])

    def test_protocol2_empty_tags(self, _):
        self.assertEqual(self.host_tags('2', ''), [])
