#!/usr/bin/env python
#
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

import os
import sys
import re
from setuptools import setup, find_packages

with open('VERSION.txt', 'r') as v:
    version = v.readline().strip()

with open('README.md', 'r') as r:
    long_description = r.read()

with open('requirements.txt') as rt:
    install_requires = rt.read().splitlines()

if sys.prefix == '/usr':
    conf_path = '/etc/patchman'
else:
    conf_path = sys.prefix + '/etc/patchman'

data_files = []
data_files.append((conf_path, ['etc/patchman-apache.conf']))

for dirpath, dirnames, filenames in os.walk('etc'):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'):
            del dirnames[i]
    if filenames:
        data_files.append(
            [conf_path, [os.path.join(dirpath, f) for f in filenames]]
        )

for dirpath, dirnames, filenames in os.walk('media'):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'):
            del dirnames[i]
    if filenames:
        data_files.append(
            [sys.prefix + '/share/patchman/media', [os.path.join(dirpath, f) for f in filenames]]
        )

setup(
    name='patchman',
    version=version,
    url='http://patchman.openbytes.ie/',
    author='Marcus Furlong',
    author_email='furlongm@gmail.com',
    description='Django based patch status monitoring tool for linux systems',
    license='GPLv3',
    keywords='django patch status monitoring linux spacewalk patchman',
    packages=find_packages(),
    install_requires=install_requires,
    data_files=data_files,
    package_data={'': ['*.html'], },
    include_package_data=True,
    scripts=['sbin/patchman',
             'sbin/patchman-set-secret-key',
             'sbin/patchman-manage',
             'sbin/patchman-migrations', ],
    long_description=long_description,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    ],
)
