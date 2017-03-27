# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2016 Marcus Furlong <furlongm@gmail.com>
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

from __future__ import print_function

import os
import sys
import requests
import bz2
import zlib
try:
    import lzma
except ImportError:
    try:
        from backports import lzma
    except ImportError:
        lzma = None
from colorama import Fore, Style
from progressbar import Bar, ETA, Percentage, ProgressBar

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'patchman.settings')
from django.conf import settings

from patchman.signals import error_message

pbar = None
verbose = None


def get_verbosity():
    """ Get the global verbosity level
    """
    global verbose
    return verbose


def set_verbosity(value):
    """ Set the global verbosity level
    """
    global verbose
    verbose = value


def create_pbar(ptext, plength, **kwargs):
    """ Create a global progress bar if global verbose is True
    """
    global pbar, verbose
    if verbose and plength > 0:
        jtext = str.ljust(ptext, 35)
        pbar = ProgressBar(widgets=[Style.RESET_ALL + Fore.YELLOW + jtext,
                                    Percentage(), Bar(), ETA()],
                           maxval=plength).start()
        return pbar


def update_pbar(index, **kwargs):
    """ Update the global progress bar if global verbose is True
    """
    global pbar, verbose
    if verbose and pbar:
        pbar.update(index)
        if index == pbar.maxval:
            pbar.finish()
            print_nocr(Fore.RESET)
            pbar = None


def download_url(res, text=''):
    """ Display a progress bar to download the request content if verbose is
        True. Otherwise, just return the request content
    """
    global verbose
    if verbose and 'content-length' in res.headers:
        clen = int(res.headers['content-length'])
        create_pbar(text, clen)
        chunk_size = 16384
        i = 0
        data = b''
        while i < clen:
            chunk = res.raw.read(chunk_size)
            i += len(chunk)
            if i <= clen:
                update_pbar(i)
            data += chunk
        if i != clen:
            update_pbar(clen)
            text = 'Data length != Content-Length '
            text += '({0!s} != {1!s})'.format(i, clen)
            error_message.send(sender=None, text=text)
        return data
    else:
        return res.content


def print_nocr(text):
    """ Print text without a carriage return
    """
    print(text, end='')
    sys.stdout.softspace = False


def get_url(url):
    """ Perform a http GET on a URL. Return None on error.
    """
    res = None
    try:
        res = requests.get(url, stream=True)
    except requests.exceptions.Timeout:
        error_message.send(sender=None, text='Timeout - {0!s}'.format(url))
    except requests.exceptions.TooManyRedirects:
        error_message.send(sender=None,
                           text='Too many redirects - {0!s}'.format(url))
    except requests.exceptions.RequestException as e:
        error_message.send(sender=None,
                           text='Error ({0!s}) - {1!s}'.format(e, url))
    return res


def response_is_valid(res):
    """ Check if a http response is valid
    """
    if res is not None:
        return res.ok
    else:
        return False


def gunzip(contents):
    """ gunzip contents in memory and return the data
    """
    try:
        wbits = zlib.MAX_WBITS | 32
        return zlib.decompress(contents, wbits)
    except zlib.error as e:
        error_message.send(sender=None, text='gunzip: ' + str(e))


def bunzip2(contents):
    """ bunzip2 contents in memory and return the data
    """
    try:
        bzip2data = bz2.decompress(contents)
        return bzip2data
    except IOError as e:
        if e == 'invalid data stream':
            error_message.send(sender=None, text='bunzip2: ' + e)
    except ValueError as e:
        if e == 'couldn\'t find end of stream':
            error_message.send(sender=None, text='bunzip2: ' + e)


def unxz(contents):
    """ unxz contents in memory and return the data
    """
    try:
        xzdata = lzma.decompress(contents)
        return xzdata
    except lzma.LZMAError as e:
        error_message.send(sender=None, text='lzma: ' + e)


def extract(data, fmt):
    """ Extract the contents based on the file ending. Return the untouched
        data if no file ending matches, else return the extracted contents.
    """
    if fmt.endswith('xz') and lzma is not None:
        return unxz(data)
    elif fmt.endswith('bz2'):
        return bunzip2(data)
    elif fmt.endswith('gz'):
        return gunzip(data)
    return data
