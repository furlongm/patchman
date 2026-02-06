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

from util.models import ClientCertificate


class Command(BaseCommand):
    help = 'Revoke a client certificate'

    def add_arguments(self, parser):
        parser.add_argument(
            'identifier',
            help='Hostname or serial number of the certificate to revoke',
        )
        parser.add_argument(
            '--reason',
            default='',
            help='Reason for revocation',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        identifier = options['identifier']

        # Try to find by hostname first, then by serial
        cert = ClientCertificate.objects.filter(
            hostname=identifier, revoked=False
        ).first()

        if not cert:
            cert = ClientCertificate.objects.filter(
                serial_number__startswith=identifier, revoked=False
            ).first()

        if not cert:
            self.stderr.write(
                self.style.ERROR(f'No active certificate found for: {identifier}')
            )
            return

        # Confirm
        if not options['force']:
            self.stdout.write('')
            self.stdout.write(f'Certificate to revoke:')
            self.stdout.write(f'  Hostname: {cert.hostname}')
            self.stdout.write(f'  Serial:   {cert.serial_number}')
            self.stdout.write(f'  Issued:   {cert.issued_at.strftime("%Y-%m-%d %H:%M")}')
            self.stdout.write(f'  Expires:  {cert.expires_at.strftime("%Y-%m-%d %H:%M")}')
            self.stdout.write('')

            confirm = input('Are you sure you want to revoke this certificate? [y/N] ')
            if confirm.lower() != 'y':
                self.stdout.write('Cancelled.')
                return

        # Revoke
        cert.revoke(reason=options['reason'])

        self.stdout.write(
            self.style.SUCCESS(
                f'Revoked certificate for {cert.hostname} (serial: {cert.serial_number})'
            )
        )
        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING(
                'Note: For full revocation, add the serial to your CA\'s CRL or OCSP.'
            )
        )
        self.stdout.write('')
