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

from django.core.management.base import BaseCommand, CommandError
from rest_framework_api_key.models import APIKey


class Command(BaseCommand):
    help = 'Revoke an API key'

    def add_arguments(self, parser):
        parser.add_argument(
            'key_or_prefix',
            type=str,
            help='The API key prefix or name to revoke'
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Permanently delete the key instead of just revoking'
        )

    def handle(self, *args, **options):
        key_input = options['key_or_prefix']
        delete = options['delete']

        # Try to find by prefix first, then by name
        api_keys = APIKey.objects.filter(prefix=key_input)
        if not api_keys.exists():
            api_keys = APIKey.objects.filter(name=key_input)

        if not api_keys.exists():
            raise CommandError(f'No API key found matching: {key_input}')
        elif api_keys.count() > 1:
            raise CommandError(f'Multiple keys match "{key_input}". Please be more specific.')

        api_key = api_keys.first()

        if delete:
            name = api_key.name
            api_key.delete()
            self.stdout.write(self.style.SUCCESS(f'Permanently deleted API key: {name}'))
        else:
            if api_key.revoked:
                self.stdout.write(self.style.WARNING(f'API key "{api_key.name}" is already revoked'))
                return

            api_key.revoked = True
            api_key.save()
            self.stdout.write(self.style.SUCCESS(f'Revoked API key: {api_key.name}'))
