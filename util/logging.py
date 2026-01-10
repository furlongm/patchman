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


import logging

from django.conf import settings
from tqdm import tqdm

from patchman.signals import (
    debug_message_s, error_message_s, info_message_s, warning_message_s,
)

log_format = '[%(asctime)s] %(levelname)s: %(message)s'
if settings.DEBUG:
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO
logging.basicConfig(level=logging_level, format=log_format)
logger = logging.getLogger()
logging.getLogger('git.cmd').setLevel(logging.WARNING)

quiet_mode = False
pbar = None


def get_quiet_mode():
    """ Get the global quiet_mode
    """
    return quiet_mode


def set_quiet_mode(value):
    """ Set the global quiet_mode
    """
    global quiet_mode
    quiet_mode = value


def create_pbar(ptext, plength, ljust=35, **kwargs):
    """ Create a global progress bar if global quiet_mode is False
    """
    global pbar
    if not quiet_mode and plength > 0:
        jtext = str(ptext).ljust(ljust)
        pbar = tqdm(total=plength, desc=jtext, position=0, leave=True, ascii=' >=')
        return pbar


def update_pbar(index, **kwargs):
    """ Update the global progress bar if global quiet_mode is False
    """
    global pbar
    if not quiet_mode and pbar:
        pbar.update(n=index-pbar.n)
        if index >= pbar.total:
            pbar.close()
            pbar = None


def info_message(text):
    info_message_s.send(sender=None, text=text)


def warning_message(text):
    warning_message_s.send(sender=None, text=text)


def debug_message(text):
    debug_message_s.send(sender=None, text=text)


def error_message(text):
    error_message_s.send(sender=None, text=text)
