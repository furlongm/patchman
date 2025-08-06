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

from django.db import IntegrityError
from patchman.signals import error_message, info_message

from modules.models import Module
from arch.models import PackageArchitecture


def get_or_create_module(name, stream, version, context, arch, repo):
    """ Get or create a module object
        Returns the module
    """
    created = False
    m_arch, c = PackageArchitecture.objects.get_or_create(name=arch)
    try:
        module, created = Module.objects.get_or_create(
            name=name,
            stream=stream,
            version=version,
            context=context,
            arch=m_arch,
            repo=repo,
        )
    except IntegrityError as e:
        error_message.send(sender=None, text=e)
        module = Module.objects.get(
            name=name,
            stream=stream,
            version=version,
            context=context,
            arch=m_arch,
            repo=repo,
        )
    return module


def get_matching_modules(name, stream, version, context, arch):
    """ Return modules that match name, stream, version, context, and arch,
        regardless of repo
    """
    m_arch, c = PackageArchitecture.objects.get_or_create(name=arch)
    modules = Module.objects.filter(
        name=name,
        stream=stream,
        version=version,
        context=context,
        arch=m_arch,
    )
    return modules


def clean_modules():
    """ Delete modules that have no host or no repo
    """
    modules = Module.objects.filter(
        host__isnull=True,
        repo__isnull=True,
    )
    mlen = modules.count()
    if mlen == 0:
        info_message.send(sender=None, text='No orphaned Modules found.')
    else:
        info_message.send(sender=None, text=f'{mlen} orphaned Modules found.')
        modules.delete()
