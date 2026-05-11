# Copyright 2024 Marcus Furlong <furlongm@gmail.com>
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

from django.core.management.base import BaseCommand
from django.utils import timezone

from patchman.util.models import ClientCertificate


class Command(BaseCommand):
    help = 'List issued client certificates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hostname',
            help='Filter by hostname (partial match)',
        )
        parser.add_argument(
            '--expired',
            action='store_true',
            help='Include expired certificates',
        )
        parser.add_argument(
            '--revoked',
            action='store_true',
            help='Include revoked certificates',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Show all certificates (including expired and revoked)',
        )

    def handle(self, *args, **options):
        certs = ClientCertificate.objects.all()

        if options['hostname']:
            certs = certs.filter(hostname__icontains=options['hostname'])

        if not options['all']:
            if not options['expired']:
                certs = certs.filter(expires_at__gt=timezone.now())
            if not options['revoked']:
                certs = certs.filter(revoked=False)

        if not certs.exists():
            self.stdout.write('No certificates found.')
            return

        # Header
        self.stdout.write('')
        self.stdout.write(
            f'{"Hostname":<40} {"Serial":<20} {"Expires":<12} {"Status":<10}'
        )
        self.stdout.write('-' * 85)

        now = timezone.now()
        for cert in certs:
            if cert.revoked:
                status = self.style.ERROR('REVOKED')
            elif cert.expires_at < now:
                status = self.style.WARNING('EXPIRED')
            elif cert.expires_at < now + timezone.timedelta(days=30):
                status = self.style.WARNING('EXPIRING')
            else:
                status = self.style.SUCCESS('ACTIVE')

            hostname = cert.hostname[:38] + '..' if len(cert.hostname) > 40 else cert.hostname
            serial = cert.serial_number[:18] + '..' if len(cert.serial_number) > 20 else cert.serial_number

            self.stdout.write(
                f'{hostname:<40} {serial:<20} '
                f'{cert.expires_at.strftime("%Y-%m-%d"):<12} {status}'
            )

        self.stdout.write('')
        self.stdout.write(f'Total: {certs.count()} certificate(s)')
        self.stdout.write('')
