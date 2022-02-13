# Copyright 2012 VPAC, http://www.vpac.org
# Copyright 2013-2021 Marcus Furlong <furlongm@gmail.com>
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
import requests
import bz2
import magic
import zlib
try:
    import lzma
except ImportError:
    try:
        from backports import lzma
    except ImportError:
        lzma = None
from colorama import Fore, Style
from enum import Enum
from hashlib import md5, sha1, sha256
from progressbar import Bar, ETA, Percentage, ProgressBar
from patchman.signals import error_message


if ProgressBar.__dict__.get('maxval'):
    pbar2 = False
else:
    pbar2 = True

pbar = None
verbose = None
Checksum = Enum('Checksum', 'md5 sha sha1 sha256')


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
        jtext = str(ptext).ljust(35)
        if pbar2:
            pbar = ProgressBar(widgets=[Style.RESET_ALL + Fore.YELLOW + jtext,
                                        Percentage(), Bar(), ETA()],
                               max_value=plength).start()
        else:
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
        if pbar2:
            pmax = pbar.max_value
        else:
            pmax = pbar.maxval
        if index == pmax:
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
        for chunk in res.iter_content(chunk_size=chunk_size, decode_unicode=False):
            i += len(chunk)
            if i > clen:
                update_pbar(clen)
            else:
                update_pbar(i)
            data += chunk
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
    """ Extract the contents based on mimetype or file ending. Return the
        unmodified data if neither mimetype nor file ending matches, otherwise
        return the extracted contents.
    """
    try:
        mime = magic.from_buffer(data, mime=True)
    except AttributeError:
        # old python-magic API
        m = magic.open(magic.MAGIC_MIME)
        m.load()
        mime = m.buffer(data).split(';')[0]
    if (mime == 'application/x-xz' or fmt.endswith('xz')) and lzma is not None:
        return unxz(data)
    elif mime == 'application/x-bzip2' or fmt.endswith('bz2'):
        return bunzip2(data)
    elif mime == 'application/gzip' or fmt.endswith('gz'):
        return gunzip(data)
    return data


def get_checksum(data, checksum_type):
    """ Returns the checksum of the data. Returns None otherwise.
    """
    if checksum_type == Checksum.sha or checksum_type == Checksum.sha1:
        checksum = get_sha1(data)
    elif checksum_type == Checksum.sha256:
        checksum = get_sha256(data)
    elif checksum_type == Checksum.md5:
        checksum = get_md5(data)
    else:
        text = 'Unknown checksum type: {0!s}'.format(checksum_type)
        error_message.send(sender=None, text=text)
    return checksum


def get_sha1(data):
    """ Return the sha1 checksum for data
    """
    return sha1(data).hexdigest()


def get_sha256(data):
    """ Return the sha256 checksum for data
    """
    return sha256(data).hexdigest()


def get_md5(data):
    """ Return the md5 checksum for data
    """
    return md5(data).hexdigest()
