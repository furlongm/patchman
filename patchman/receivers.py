# Copyright 2012 VPAC, http://www.vpac.org
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

import os

from django.dispatch import receiver

from util import create_pbar, update_pbar, print_nocr, get_verbosity
from signals import progress_info_s, progress_update_s, \
    info_message, error_message, debug_message

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patchman.settings")
from django.conf import settings


@receiver(progress_info_s)
def progress_info_r(**kwargs):

    ptext = kwargs.get('ptext')
    plen = kwargs.get('plen')
    if ptext and plen:
        create_pbar(ptext, plen)


@receiver(progress_update_s)
def progress_update_r(**kwargs):

    index = kwargs.get('index')
    if index:
        update_pbar(index)


@receiver(info_message)
def print_info_message(sender=None, **kwargs):

    text = kwargs.get('text')
    if get_verbosity():
        print_nocr(text)


@receiver(error_message)
def print_error_message(sender, **kwargs):

    text = kwargs.get('text')
    if text:
        print_nocr(text)


@receiver(debug_message)
def print_debug_message(sender, **kwargs):

    text = kwargs.get('text')
    if get_verbosity() and settings.DEBUG and text:
        print_nocr(text)
