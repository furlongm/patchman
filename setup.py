from setuptools import setup
import os

with open('VERSION.txt', 'r') as f:
    version = f.readline().strip()


def fullsplit(path, result=None):
    """
    Split a pathname into components (the opposite of os.path.join) in a
    platform-neutral way.
    """
    if result is None:
        result = []
    head, tail = os.path.split(path)
    if head == '':
        return [tail] + result
    if head == path:
        return result
    return fullsplit(head, [tail] + result)

packages = []
for dirpath, dirnames, filenames in os.walk('patchman'):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'):
            del dirnames[i]
    if filenames:
        packages.append('.'.join(fullsplit(dirpath)))

data_files = [
              ('/etc/patchman', ['etc/patchman-apache.conf']),
]
for dirpath, dirnames, filenames in os.walk('etc'):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'): del dirnames[i]
    if filenames:
       data_files.append([dirpath.replace('etc', '/etc/patchman'), [os.path.join(dirpath, f) for f in filenames]])

for dirpath, dirnames, filenames in os.walk('media'):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'): del dirnames[i]
    if filenames:
        data_files.append([dirpath.replace('media', '/usr/share/patchman/media'), [os.path.join(dirpath, f) for f in filenames]])

for dirpath, dirnames, filenames in os.walk('templates'):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'): del dirnames[i]
    if filenames:
        data_files.append([dirpath.replace('templates', '/usr/share/patchman/templates'), [os.path.join(dirpath, f) for f in filenames]])

setup(
    name = 'patchman',
    version = version,
    url = 'https://www.github.com/furlongm/patchman/',
    author = 'Marcus Furlong',
    author_email = 'furlongm@gmail.com',
    description = 'Patchman is a django-based patch status monitoring tool for linux systems.',
    packages = packages,
    data_files = data_files,
    scripts = ['sbin/patchman', 'sbin/patchman-set-secret-key'],
)
