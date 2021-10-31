#!/usr/bin/env python3
#
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

import os
from setuptools import setup, find_packages

with open('VERSION.txt', 'r') as v:
    version = v.readline().strip()

with open('README.md', 'r') as r:
    long_description = r.read()

with open('requirements.txt') as rt:
    install_requires = rt.read().splitlines()


data_files = []

for dirpath, dirnames, filenames in os.walk('etc'):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'):
            del dirnames[i]
    if filenames:
        data_files.append(
            ['/etc/patchman', [os.path.join(dirpath, f) for f in filenames]]
        )

for dirpath, dirnames, filenames in os.walk('patchman/static'):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'):
            del dirnames[i]
    if filenames:
        data_files.append(
            ['/usr/share/' + dirpath,
             [os.path.join(dirpath, f) for f in filenames]]
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
             'sbin/patchman-manage', ],
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    ],
)
