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

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from util.models import EnrollmentToken


class Command(BaseCommand):
    help = 'Create an enrollment token for client certificate enrollment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hostname',
            help='Hostname pattern (glob), e.g., "*.example.com". Empty allows any hostname.',
        )
        parser.add_argument(
            '--expires',
            default='24h',
            help='Expiry time (e.g., 1h, 24h, 7d, 30d). Default: 24h',
        )
        parser.add_argument(
            '--multi-use',
            action='store_true',
            help='Allow token to be used multiple times (default is single-use)',
        )
        parser.add_argument(
            '--notes',
            default='',
            help='Optional notes about this token',
        )
        parser.add_argument(
            '--created-by',
            default='',
            help='Record who created this token',
        )

    def handle(self, *args, **options):
        # Parse expiry
        expiry_str = options['expires'].lower()
        try:
            if expiry_str.endswith('h'):
                delta = timedelta(hours=int(expiry_str[:-1]))
            elif expiry_str.endswith('d'):
                delta = timedelta(days=int(expiry_str[:-1]))
            elif expiry_str.endswith('m'):
                delta = timedelta(minutes=int(expiry_str[:-1]))
            else:
                # Assume hours if no suffix
                delta = timedelta(hours=int(expiry_str))
        except ValueError:
            self.stderr.write(
                self.style.ERROR(f'Invalid expiry format: {expiry_str}')
            )
            return

        token = EnrollmentToken.objects.create(
            hostname_pattern=options['hostname'] or '',
            expires=timezone.now() + delta,
            single_use=not options['multi_use'],
            notes=options['notes'],
            created_by=options['created_by'],
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Enrollment Token Created'))
        self.stdout.write('=' * 50)
        self.stdout.write(f'Token:      {token.token}')
        self.stdout.write(f'Hostname:   {token.hostname_pattern or "(any)"}')
        self.stdout.write(f'Expires:    {token.expires.strftime("%Y-%m-%d %H:%M:%S %Z")}')
        self.stdout.write(f'Usage:      {"multi-use" if not token.single_use else "single-use"}')
        if token.notes:
            self.stdout.write(f'Notes:      {token.notes}')
        self.stdout.write('')
        self.stdout.write('Client usage:')
        self.stdout.write(f'  patchman-client.py --enroll --token {token.token}')
        self.stdout.write('')
