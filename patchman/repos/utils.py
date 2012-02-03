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

import bz2
import gzip
from hashlib import sha1, sha256
from StringIO import StringIO
from lxml import etree
#from debian.debian_support import Version
#from debian.deb822 import Sources
#from urllib2 import Request, urlopen


def gunzip(contents):

    try:
        gzipdata = gzip.GzipFile(fileobj=contents)
        gzipdata = gzipdata.read()
        contents = StringIO(gzipdata)
    except IOError, e:
        import warnings
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        if e.message == 'Not a gzipped file':
            pass

    return contents.getvalue()


def bunzip2(contents):

    try:
        bzip2data = bz2.decompress(contents)
        return bzip2data
    except IOError, e:
        if e == 'invalid data stream':
            pass


def extract(data):

    extracted = bunzip2(data)
    if not extracted:
        extracted = gunzip(StringIO(data))
    return extracted


def get_primary_url(repo_url, data):

    ns = 'http://linux.duke.edu/metadata/repo'
    context = etree.parse(StringIO(data), etree.XMLParser())
    location = context.xpath("//ns:data[@type='primary']/ns:location/@href", namespaces={'ns': ns})[0]
    checksum = context.xpath("//ns:data[@type='primary']/ns:checksum", namespaces={'ns': ns})[0].text
    checksum_type = context.xpath("//ns:data[@type='primary']/ns:checksum/@type", namespaces={'ns': ns})[0]
    primary_url = str(repo_url.rsplit('/', 2)[0]) + '/' + location
    return primary_url, checksum, checksum_type


def get_sha1(data):

    return sha1(data).hexdigest()


def get_sha256(data):

    return sha256(data).hexdigest()
