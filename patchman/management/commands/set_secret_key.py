import os
import re
import sys
import codecs
from random import choice
from tempfile import NamedTemporaryFile
from shutil import copy

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Set SECRET_KEY of Patchman Application.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--key', help=(
                'The SECRET_KEY to be used by Patchman. If not set, a random '
                'key of length 50 will be created.'))

    @staticmethod
    def get_random_key():
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        return ''.join([choice(chars) for i in range(50)])

    def handle(self, *args, **options):
        secret_key = options.get('key', self.get_random_key())

        if sys.prefix == '/usr':
            conf_path = '/etc/patchman'
        else:
            conf_path = os.path.join(sys.prefix, 'etc/patchman')
            # if conf_path doesn't exist, try ./etc/patchman
            if not os.path.isdir(conf_path):
                conf_path = './etc/patchman'
        local_settings = os.path.join(conf_path, 'local_settings.py')

        settings_contents = codecs.open(
            local_settings, 'r', encoding='utf-8').read()
        settings_contents = re.sub(
            r"(?<=SECRET_KEY = ')'", secret_key + "'", settings_contents)

        f = NamedTemporaryFile(delete=False)
        temp = f.name
        f.close()

        fh = codecs.open(temp, 'w+b', encoding='utf-8')
        fh.write(settings_contents)
        fh.close()

        copy(temp, local_settings)
        os.remove(temp)
