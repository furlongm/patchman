from django.core.management.base import BaseCommand, CommandError
from hosts.models import Host


class Command(BaseCommand):
    help = 'Enable/Disable rDNS check for hosts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--disable', action='store_false', default=True, dest='rdns_check',
            help='If set, disables rDNS check')

    def handle(self, *args, **options):
        try:
            Host.objects.all().update(check_dns=options['rdns_check'])
        except Exception as e:
            raise CommandError('Failed to update rDNS check', str(e))
