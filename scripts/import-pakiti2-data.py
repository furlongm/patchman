#!/usr/bin/env python

from django.core.management import setup_environ

import os
import sys
import MySQLdb
import string

sys.path.append('/usr/local/src')

os.environ['DJANGO_SETTINGS_MODULE'] = 'patchman.settings'

from patchman import settings
setup_environ(settings)

from django.db.utils import IntegrityError

from patchman.hosts.models import Host
from patchman.operatingsystems.models import OS, OSGroup
from patchman.domains.models import Domain
from patchman.packages.models import Package, PackageName
from patchman.repos.models import Repository
from patchman.arch.models import PackageArchitecture, MachineArchitecture

from progressbar import Bar, ETA, Percentage, ProgressBar

def progress_bar(ptext, plength):

    jtext = string.ljust(ptext, 30)
    pbar = ProgressBar(widgets=[jtext, Percentage(), Bar(), ETA()], maxval=plength).start()
    return pbar

def import_domains(conn):

    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('SELECT * FROM domain')
    rows = cursor.fetchall()

    plength = len(rows)
    pbar = progress_bar('Domains', plength)
    i = 0

    for row in rows:
        domain, c = Domain.objects.get_or_create(id=row['id'], name=row['domain'])
        pbar.update(i+1)
        i += 1
    cursor.close()

def import_os(conn):

    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM os_group')
    rows = cursor.fetchall()

    plength = len(rows)
    pbar = progress_bar('OS Groups', plength)
    i = 0

    for row in rows:
        pbar.update(i+1)
        i += 1
        try:
            osgroup, c = OSGroup.objects.get_or_create(id=row['id'], name=row['name'])
        except(IntegrityError):
            print "IntegrityError"
            continue

    cursor.close()

    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM os')
    rows = cursor.fetchall()

    plength = len(rows)
    pbar = progress_bar('OSs', plength)
    i = 0

    for row in rows:
        pbar.update(i+1)
        i += 1
        try:
            os, c = OS.objects.get_or_create(id=row['id'], name=row['os'])
        except(IntegrityError):
            print "IntegrityError"
            continue

    cursor.close()

    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM oses_group')
    rows = cursor.fetchall()

    plength = len(rows)
    pbar = progress_bar('Creating OS<->Group Mappings', plength)
    i = 0

    for row in rows:
        pbar.update(i+1)
        i += 1
        osgroup = OSGroup.objects.get(id=row['os_group_id'])
        this_os = OS.objects.get(id=row['os_id'])
        this_os.osgroup = osgroup
        this_os.save()

    cursor.close()

def import_arch(conn):

    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM arch')
    rows = cursor.fetchall()

    plength = len(rows)
    pbar = progress_bar('Machine Architectures', plength)
    i = 0

    for row in rows:
        pbar.update(i+1)
        i += 1 
        try:
            arch, c = MachineArchitecture.objects.get_or_create(id=row['id'], name=row['arch'])
        except(IntegrityError):
            print "IntegrityError"
            continue

    cursor.close()

    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT DISTINCT arch FROM act_version')
    rows = cursor.fetchall()

    plength = len(rows)
    pbar = progress_bar('Package Architectures', plength)
    i = 0

    for row in rows:
        pbar.update(i+1)
        i += 1
        try:
            arch, c = PackageArchitecture.objects.get_or_create(name=row['arch'])
        except(IntegrityError):
            print "IntegrityError"
            continue

    cursor.close()


def import_hosts(conn):
    
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM host')
    rows = cursor.fetchall()

    plength = len(rows)
    pbar = progress_bar('Hosts', plength)
    i = 0

    for row in rows:
        pbar.update(i+1)
        i += 1
        
        host, created = Host.objects.get_or_create(
            hostname=row['host'],
            id=row['id'],
            arch=MachineArchitecture.objects.get(id=row['arch_id']),
            defaults={
                'ipaddress': row['report_ip'],
                'os': OS.objects.get(id=row['os_id']),
                'domain': Domain.objects.get(id=row['dmn_id']),
                'lastreport': row['pkgs_change_timestamp'],
                },
            tag=row['admin'],
            kernel=row['kernel']
            )
    cursor.close()

def import_package_names(conn):

    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM pkgs')
    rows = cursor.fetchall()

    plength = len(rows)
    pbar = progress_bar('Package Names', plength)
    i = 0

    for row in rows:
        package, c = PackageName.objects.get_or_create(id=row['id'], name=row['name'].lower())
        pbar.update(i+1)
        i += 1

    cursor.close()

def import_repos(conn):

    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM repositories')
    rows = cursor.fetchall()

    plength = len(rows)
    pbar = progress_bar('Repositories', plength)
    i = 0

    for row in rows:
        repo, c = Repository.objects.get_or_create(
            id=row['id'], name=row['name'], url=row['url'], security=row['is_sec'], enabled=row['enabled'],last_access_ok=row['last_access_ok'], file_checksum=row['file_checksum'], timestamp=row['timestamp'], arch=MachineArchitecture.objects.get(id=row['arch_id']))
        if row['type'] == "dpkg":
            repotype="D"
        elif row['type'] == "rpm":
            repotype="R"
        repo.repotype = repotype
        repo.save()
        pbar.update(i+1)
        i += 1

    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT pkgs.name, act_version.arch, act_version.act_version, act_version.act_rel, repositories.id FROM (act_version inner join repositories on act_version.repo_id = repositories.id) inner join pkgs on act_version.pkg_id = pkgs.id')
    rows = cursor.fetchall()

    plength = len(rows)
    pbar = progress_bar('Creating Package<->Repo Links', plength)
    i = 0

    for row in rows:
        repo = Repository.objects.get(id=row['id'])
        p_name = PackageName.objects.get(name=row['name'])
        try:
            package = Package.objects.get(name=p_name,release=row['act_rel'], version=row['act_version'], arch=PackageArchitecture.objects.get(name=row['arch']))
            repo.packages.add(package)
        except Package.DoesNotExist:
            print 'Package does not exist: %s %s %s %s %s %s %s' % (row['name'], p_name, p_name.id, row['act_rel'], row['act_version'], row['arch'], PackageArchitecture.objects.get(name=row['arch']).id)
        repo.save()
        pbar.update(i+1)
        i += 1

    cursor.close()

def import_available_packages(conn):

    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM act_version')
    rows = cursor.fetchall()

    plength = len(rows)
    pbar = progress_bar('Available Packages', plength)
    i = 0

    for row in rows:
        package, c = Package.objects.get_or_create(name=PackageName.objects.get(id=row['pkg_id']), version=row['act_version'], release=row['act_rel'], arch=PackageArchitecture.objects.get(name=row['arch']))
#        print PackageName.objects.get(id=row['pkg_id'])
#        print package.name
#        print row['pkg_id']
#        print row['act_version']
#        print '\n\n'
        pbar.update(i+1)
        i += 1
    cursor.close()

def import_installed_packages(conn):

    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM installed_pkgs')
    rows = cursor.fetchall()

    plength = len(rows)
    pbar = progress_bar('Installed Packages', plength)
    i = 0

    for row in rows:
        pbar.update(i+1)
        i += 1
        try:
            host = Host.objects.get(id=row['host_id'])
        except Host.DoesNotExist:
            continue
        arch, c = PackageArchitecture.objects.get_or_create(name=row['arch'])
        package, c = Package.objects.get_or_create(name=PackageName.objects.get(id=row['pkg_id']), version=row['version'], release=row['rel'], arch=arch)
        host.packages.add(package)

    cursor.close()

if __name__ == "__main__":

    conn = MySQLdb.connect (
        host = 'db.vpac.org',
        user = 'pakiti',
        passwd = 'paD9T93qy29HDFVV',
        db = 'pakiti')

    print "Importing Data from Pakiti"
    
    import_arch(conn)
    import_os(conn)
    import_domains(conn)
    import_hosts(conn)
    import_package_names(conn)
    import_available_packages(conn)
    import_repos(conn)
    import_installed_packages(conn)
    conn.close()
