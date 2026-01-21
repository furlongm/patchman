from django.contrib.auth.management.commands import createsuperuser
from django.core.management import CommandError


class Command(createsuperuser.Command):
    help = 'Crate a superuser, and allow password to be provided'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--password', dest='password', default=None,
            help='Specifies the password for the superuser.',
        )

    def handle(self, *args, **options):
        password = options.get('password')
        username = options.get('username')
        database = options.get('database')

        if options['interactive']:
            raise CommandError(
                'Command is required to run with --no-input option')
        if password and not username:
            raise CommandError(
                '--username is required if specifying --password')

        super(Command, self).handle(*args, **options)

        if password:
            user = self.UserModel._default_manager.db_manager(
                database).get(username=username)
            user.set_password(password)
            user.save()
