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
    help = 'Create a new API key for protocol 2 report uploads'

    def add_arguments(self, parser):
        parser.add_argument(
            'name',
            type=str,
            help='Descriptive name for this API key (e.g., "webserver-cluster")'
        )

    def handle(self, *args, **options):
        name = options['name']

        api_key, key = APIKey.objects.create_key(name=name)

        self.stdout.write(self.style.SUCCESS(f'Created API key: {name}'))
        self.stdout.write('')
        self.stdout.write(f'  Key: {key}')
        self.stdout.write('')
        self.stdout.write('Add this to your patchman-client.conf:')
        self.stdout.write(f'  api_key={key}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Save this key - it cannot be retrieved later!'))
