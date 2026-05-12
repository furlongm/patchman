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

from patchman.util.models import EnrollmentToken


class Command(BaseCommand):
    help = 'List enrollment tokens'

    def add_arguments(self, parser):
        parser.add_argument(
            '--expired',
            action='store_true',
            help='Include expired tokens',
        )
        parser.add_argument(
            '--used',
            action='store_true',
            help='Include used tokens',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Show all tokens (including expired and used)',
        )

    def handle(self, *args, **options):
        tokens = EnrollmentToken.objects.all()

        if not options['all']:
            if not options['expired']:
                tokens = tokens.filter(expires__gt=timezone.now())
            if not options['used']:
                tokens = tokens.filter(used_by='')

        if not tokens.exists():
            self.stdout.write('No enrollment tokens found.')
            return

        # Header
        self.stdout.write('')
        self.stdout.write(
            f'{"Token":<25} {"Hostname Pattern":<25} {"Expires":<20} {"Status":<10}'
        )
        self.stdout.write('-' * 85)

        now = timezone.now()
        for token in tokens:
            if token.used_by:
                status = self.style.WARNING(f'USED ({token.used_by[:15]})')
            elif token.expires < now:
                status = self.style.ERROR('EXPIRED')
            else:
                status = self.style.SUCCESS('ACTIVE')

            token_short = token.token[:23] + '..'
            pattern = token.hostname_pattern[:23] + '..' if len(token.hostname_pattern) > 25 else (token.hostname_pattern or '(any)')

            self.stdout.write(
                f'{token_short:<25} {pattern:<25} '
                f'{token.expires.strftime("%Y-%m-%d %H:%M"):<20} {status}'
            )

        self.stdout.write('')
        self.stdout.write(f'Total: {tokens.count()} token(s)')
        self.stdout.write('')
