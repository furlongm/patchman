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

import requests
import bz2
import magic
import zlib
import lzma
import os
from datetime import datetime, timezone
from enum import Enum
from hashlib import md5, sha1, sha256, sha512
from requests.exceptions import HTTPError, Timeout, ConnectionError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from time import time
from tqdm import tqdm

from django.utils.timezone import make_aware
from django.utils.dateparse import parse_datetime
from django.conf import settings

from patchman.signals import error_message, info_message, debug_message

pbar = None
verbose = None
Checksum = Enum('Checksum', 'md5 sha sha1 sha256 sha512')

http_proxy = os.getenv('http_proxy')
https_proxy = os.getenv('https_proxy')
proxies = {
   'http': http_proxy,
   'https': https_proxy,
}


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


def create_pbar(ptext, plength, ljust=35, **kwargs):
    """ Create a global progress bar if global verbose is True
    """
    global pbar, verbose
    if verbose and plength > 0:
        jtext = str(ptext).ljust(ljust)
        pbar = tqdm(total=plength, desc=jtext, position=0, leave=True, ascii=' >=')
        return pbar


def update_pbar(index, **kwargs):
    """ Update the global progress bar if global verbose is True
    """
    global pbar, verbose
    if verbose and pbar:
        pbar.update(n=index-pbar.n)
        if index >= pbar.total:
            pbar.close()
            pbar = None


def fetch_content(response, text='', ljust=35):
    """ Display a progress bar to fetch the request content if verbose is
        True. Otherwise, just return the request content
    """
    global verbose
    if not response:
        return
    if verbose:
        content_length = response.headers.get('content-length')
        if content_length:
            clen = int(content_length)
            create_pbar(text, clen, ljust)
            chunk_size = 16384
            i = 0
            data = b''
            for chunk in response.iter_content(chunk_size=chunk_size, decode_unicode=False):
                i += len(chunk)
                if i > clen:
                    update_pbar(clen)
                else:
                    update_pbar(i)
                data += chunk
            return data
        else:
            info_message.send(sender=None, text=text)
    return response.content


@retry(
    retry=retry_if_exception_type(HTTPError | Timeout | ConnectionResetError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=False,
)
def get_url(url, headers={}, params={}):
    """ Perform a http GET on a URL. Return None on error.
    """
    response = None
    try:
        debug_message.send(sender=None, text=f'Trying {url} headers:{headers} params:{params}')
        response = requests.get(url, headers=headers, params=params, stream=True, proxies=proxies, timeout=30)
        debug_message.send(sender=None, text=f'{response.status_code}: {response.headers}')
        if response.status_code in [403, 404]:
            return response
        response.raise_for_status()
    except requests.exceptions.TooManyRedirects:
        error_message.send(sender=None, text=f'Too many redirects - {url}')
    except ConnectionError:
        error_message.send(sender=None, text=f'Connection error - {url}')
    return response


def response_is_valid(response):
    """ Check if a http response is valid
    """
    if response:
        return response.ok
    else:
        return False


def has_setting_of_type(setting_name, expected_type):
    """ Checks if the Django settings module has the specified attribute
        and if it is of the expected type
        Returns True if the setting exists and is of the expected type, False otherwise.
    """
    if not hasattr(settings, setting_name):
        return False
    setting_value = getattr(settings, setting_name)
    return isinstance(setting_value, expected_type)


def get_setting_of_type(setting_name, setting_type, default):
    """ Checks if the Django settings module has the specified attribute
        and if it is of the expected type
        Returns the value if the setting exists and is of the expected type, default otherwise.
    """
    if has_setting_of_type(setting_name, setting_type):
        setting_value = getattr(settings, setting_name)
        return setting_value
    else:
        return default


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
        if e == "couldn't find end of stream":
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
    if mime == 'application/x-xz' or fmt.endswith('xz'):
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
    elif checksum_type == Checksum.sha512:
        checksum = get_sha512(data)
    elif checksum_type == Checksum.md5:
        checksum = get_md5(data)
    else:
        text = f'Unknown checksum type: {checksum_type}'
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


def get_sha512(data):
    """ Return the sha512 checksum for data
    """
    return sha512(data).hexdigest()


def get_md5(data):
    """ Return the md5 checksum for data
    """
    return md5(data).hexdigest()


def is_epoch_time(timestamp):
    """ Checks if an integer is likely a valid epoch timestamp.
        Returns True if the integer is likely a valid epoch timestamp, False otherwise.
    """
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    current_time = int(time())
    lower_bound = 0
    upper_bound = current_time + 3600 * 24 * 365  # up to a year in the future
    return lower_bound <= ts <= upper_bound


def tz_aware_datetime(date):
    """ Ensure a datetime is timezone-aware
        Returns the tz-aware datetime object
    """
    if isinstance(date, int) or is_epoch_time(date):
        parsed_date = datetime.fromtimestamp(int(date))
    elif isinstance(date, str):
        parsed_date = parse_datetime(date)
    else:
        parsed_date = date
    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
    if not parsed_date.tzinfo:
        parsed_date = make_aware(parsed_date)
    return parsed_date


def get_datetime_now():
    """ Return the current timezone-aware datetime removing microseconds
    """
    return datetime.now().astimezone().replace(microsecond=0)
