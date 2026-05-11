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

from django.core.management.base import BaseCommand
from rest_framework_api_key.models import APIKey


class Command(BaseCommand):
    help = 'List all API keys'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Show all keys including revoked ones'
        )

    def handle(self, *args, **options):
        if options['all']:
            api_keys = APIKey.objects.all()
        else:
            api_keys = APIKey.objects.filter(revoked=False)

        if not api_keys.exists():
            self.stdout.write('No API keys found.')
            return

        self.stdout.write('')
        self.stdout.write(f'{"Name":<30} {"Prefix":<12} {"Created":<20} {"Revoked":<8}')
        self.stdout.write('-' * 72)

        for key in api_keys:
            created = key.created.strftime('%Y-%m-%d %H:%M')
            revoked = 'Yes' if key.revoked else 'No'

            self.stdout.write(f'{key.name:<30} {key.prefix:<12} {created:<20} {revoked:<8}')

        self.stdout.write('')
        self.stdout.write(f'Total: {api_keys.count()} key(s)')
