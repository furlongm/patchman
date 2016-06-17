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


def find_versions(s):
    """ Given a package version string, return the epoch, version, release """

    epoch = find_epoch(s)
    release = find_release(s)
    version = find_version(s, epoch, release)

    return epoch, version, release


def find_release(s):
    """ Given a package version string, return the release """

    r = s.rpartition('-')
    if r[0] == '':
        return ''
    else:
        return r[2]


def find_epoch(s):
    """ Given a package version string, return the epoch """

    r = s.partition(':')
    if r[1] == '':
        return ''
    else:
        return r[0]


def find_version(s, epoch, release):
    """ Given a package version string, return the version """

    try:
        es = '{0!s}:'.format(epoch)
        e = s.index(es) + len(epoch) + 1
    except ValueError:
        e = 0
    try:
        rs = '-{0!s}'.format(release)
        r = s.index(rs)
    except ValueError:
        r = len(s)
    return s[e:r]
