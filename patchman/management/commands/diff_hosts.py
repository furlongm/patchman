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

import sys

from django.core.management.base import BaseCommand

from patchman.management.helpers import get_hosts
from patchman.util.logging import info_message, set_quiet_mode


class Command(BaseCommand):
    help = 'Show differences between two hosts in diff-like output'

    def add_arguments(self, parser):
        parser.add_argument(
            'hostA',
            type=str,
            help='First host (FQDN substring)',
        )
        parser.add_argument(
            'hostB',
            type=str,
            help='Second host (FQDN substring)',
        )

    def handle(self, *args, **options):
        set_quiet_mode(options['verbosity'] == 0)
        hosts_to_compare = get_hosts(
            [options['hostA'], options['hostB']], 'Retrieving info',
        )

        if len(hosts_to_compare) != 2:
            sys.exit(1)

        hostA = hosts_to_compare[0]
        hostB = hosts_to_compare[1]
        packagesA = set(hostA.packages.all())
        packagesB = set(hostB.packages.all())
        reposA = set(hostA.repos.all())
        reposB = set(hostB.repos.all())

        package_diff_AB = packagesA.difference(packagesB)
        package_diff_BA = packagesB.difference(packagesA)
        repo_diff_AB = reposA.difference(reposB)
        repo_diff_BA = reposB.difference(reposA)

        info_message(text=f'+ {hostA.hostname}')
        info_message(text=f'- {hostB.hostname}')

        if hostA.os != hostB.os:
            info_message(text='\nOperating Systems')
            info_message(text=f'+ {hostA.os}')
            info_message(text=f'- {hostB.os}')
        else:
            info_message(text='\nNo OS differences')

        if hostA.arch != hostB.arch:
            info_message(text='\nArchitecture')
            info_message(text=f'+ {hostA.arch}')
            info_message(text=f'- {hostB.arch}')
        else:
            info_message(text='\nNo Architecture differences')

        if hostA.kernel != hostB.kernel:
            info_message(text='\nKernels')
            info_message(text=f'+ {hostA.kernel}')
            info_message(text=f'- {hostB.kernel}')
        else:
            info_message(text='\nNo Kernel differences')

        if len(package_diff_AB) != 0 or len(package_diff_BA) != 0:
            info_message(text='\nPackages')
            for package in package_diff_AB:
                info_message(text=f'+ {package}')
            for package in package_diff_BA:
                info_message(text=f'- {package}')
        else:
            info_message(text='\nNo Package differences')

        if len(repo_diff_AB) != 0 or len(repo_diff_BA) != 0:
            info_message(text='\nRepositories')
            for repo in repo_diff_AB:
                info_message(text=f'+ {repo}')
            for repo in repo_diff_BA:
                info_message(text=f'- {repo}')
        else:
            info_message(text='\nNo Repo differences')
