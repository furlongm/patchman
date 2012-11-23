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

import string
import math
from progressbar import Bar, ETA, Percentage, ProgressBar

from django.core.management import setup_environ

from patchman.conf import settings
setup_environ(settings)

pbar = None


def create_pbar(ptext, plength, **kwargs):

    global pbar
    if settings.VERBOSE and plength > 0:
        jtext = string.ljust(ptext, 35)
        pbar = ProgressBar(widgets=[jtext, Percentage(), Bar(), ETA()], maxval=plength).start()
        return pbar


def update_pbar(index, **kwargs):

    global pbar
    if settings.VERBOSE and pbar:
        pbar.update(index)
        if index == pbar.maxval:
            pbar.finish()
            pbar = None


def download_url(res, text=''):

    headers = dict(res.headers.items())
    verbose = settings.VERBOSE
    if verbose and 'content-length' in headers:
        clen = int(headers['content-length'])
        chunk_size = 16384.0
        create_pbar(text, clen)
        i = 0
        chunks = int(math.ceil(clen / chunk_size))
        data = ''
        chunk = ''
        for x in range(1, chunks + 1):
            chunk = res.read(int(chunk_size))
            i += len(chunk)
            update_pbar(i)
            data += chunk
        return data
    else:
        return res.read()
