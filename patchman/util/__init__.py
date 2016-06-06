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
import sys
import string

from progressbar import Bar, ETA, Percentage, ProgressBar

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patchman.settings")
from django.conf import settings

pbar = None
verbose = None


def get_verbosity():

    global verbose
    return verbose


def set_verbosity(value):

    global verbose
    verbose = value


def create_pbar(ptext, plength, **kwargs):

    global pbar, verbose
    if verbose and plength > 0:
        jtext = string.ljust(ptext, 35)
        pbar = ProgressBar(widgets=[jtext, Percentage(), Bar(), ETA()],
                           maxval=plength).start()
        return pbar


def update_pbar(index, **kwargs):

    global pbar, verbose
    if verbose and pbar:
        pbar.update(index)
        if index == pbar.maxval:
            pbar.finish()
            pbar = None


def download_url(res, text=''):

    global verbose
    if verbose and 'content-length' in res.headers:
        clen = int(res.headers['content-length'])
        create_pbar(text, clen)
        chunk_size = 16384
        i = 0
        data = ''
        for chunk in res.iter_content(chunk_size):
            i += len(chunk)
            update_pbar(i)
            data += chunk
        return data
    else:
        return res.content


def print_nocr(text):
    print text,
    sys.stdout.softspace = False
