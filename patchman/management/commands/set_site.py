from django.core.management.base import BaseCommand, CommandError
from django.contrib.sites.models import Site
from django.conf import settings


class Command(BaseCommand):
    help = 'Set Patchman Site Name'

    def add_arguments(self, parser):
        parser.add_argument(
            '-n', '--name', dest='site_name', help='Site name')
        parser.add_argument(
            '--clear-cache', action='store_true', default=False,
            dest='clear_cache', help='Clear Site cache')

    def handle(self, *args, **options):
        try:
            Site.objects.filter(pk=settings.SITE_ID).update(
                name=options['site_name'], domain=options['site_name'])
            if options['clear_cache']:
                Site.objects.clear_cache()
        except Exception as e:
            raise CommandError('Failed to update Site name', str(e))
