#!/usr/bin/env python

import os
import sys
import argparse

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "patchman.settings")
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Count
from django import setup as django_setup

django_setup()

from datetime import date, datetime
from tagging.models import TaggedItem

from patchman.hosts.models import Host
from patchman.packages.models import Package, PackageName, PackageUpdate
from patchman.repos.models import Repository
from patchman.arch.models import PackageArchitecture, MachineArchitecture
from patchman.reports.models import Report
from patchman.receivers import print_info_message, print_debug_message, \
    print_error_message
from patchman.util import create_pbar, update_pbar, set_verbosity, verbose


def get_host(host=None, action='Performing action'):
    """ Helper function to get a single host object
    """

    host_obj = None
    hostdot = host + '.'
    message = '%s for host %s' % (action, host)

    try:
        host_obj = Host.objects.get(hostname__startswith=hostdot)
    except ObjectDoesNotExist:
        try:
            host_obj = Host.objects.get(hostname__startswith=host)
        except ObjectDoesNotExist:
            message = 'Host %s does not exist' % host
    except MultipleObjectsReturned:
        matches = Host.objects.filter(hostname__startswith=host).count()
        message = '%s hosts match hostname "%s"' % (matches, host)

    if verbose:
        print message

    return host_obj


def get_hosts(hosts=None, action='Performing action'):
    """ Helper function to get a list of hosts
    """

    host_objs = []

    if hosts:
        if type(hosts) == str:
            host_obj = get_host(hosts, action)
            if host_obj is not None:
                host_objs.append(host_obj)
        elif type(hosts) == list:
            for host in hosts:
                host_obj = get_host(host, action)
                if host_obj is not None:
                    host_objs.append(host_obj)
    else:
        if verbose:
            print '%s for all hosts' % action
        host_objs = Host.objects.all()

    return host_objs


def get_repos(repo=None, action='Performing action', only_enabled=False):
    """ Helper function to get a list of repos
    """

    repos = []

    if repo:
        try:
            repos.append(Repository.objects.get(id=repo))
            message = '%s for repo %s' % (action, repo)
        except:
            message = 'Repo %s does not exist' % repo
    else:
        message = '%s for all repos' % action
        if only_enabled:
            repos = Repository.objects.filter(enabled=True)
        else:
            repos = Repository.objects.all()

    if verbose:
        print message

    return repos


def refresh_repos(repo=None, force=False):
    """ Refresh metadata for all enabled repos.
        Specify a repo ID to update a single repo.
    """

    repos = get_repos(repo, 'Refreshing metadata', True)

    for repo in repos:
        if verbose:
            print '%s' % repo
        repo.refresh(force)
        if verbose:
            print '\n'


def list_repos(repos=None):
    """ Print info about a list of repositories
        Defaults to all repos
    """

    matching_repos = get_repos(repos, 'Printing information')

    for repo in matching_repos:
        repo.show()


def list_hosts(hosts=None):
    """ Print info about a list of hosts
        Defaults to all hosts
    """

    matching_hosts = get_hosts(hosts, 'Printing information')

    for host in matching_hosts:
        host.show()


def clean_packages():
    """ Removes packages that are no longer in use
    """

    packages = Package.objects.filter(mirror__isnull=True, host__isnull=True)
    plen = packages.count()
    if plen == 0:
        if verbose:
            print 'No orphaned packages found.'
    else:
        create_pbar('Removing %s orphaned packages:' % plen, plen)
        for i, o in enumerate(packages):
            p = Package.objects.get(name=o.name,
                                    epoch=o.epoch,
                                    version=o.version,
                                    release=o.release,
                                    arch=o.arch,
                                    packagetype=o.packagetype)
            p.delete()
            update_pbar(i + 1)


def clean_arches():
    """ Removes architectures that are no longer in use
    """

    parches = PackageArchitecture.objects.filter(package__isnull=True)
    plen = parches.count()

    if plen == 0:
        if verbose:
            print 'No orphaned package architectures found.'
    else:
        create_pbar('Removing %s orphaned p arches:' % plen, plen)
        for i, p in enumerate(parches):
            a = PackageArchitecture.objects.get(name=p.name)
            a.delete()
            update_pbar(i + 1)

    marches = MachineArchitecture.objects.filter(host__isnull=True,
                                                 repository__isnull=True)
    mlen = marches.count()

    if mlen == 0:
        if verbose:
            print 'No orphaned machine architectures found.'
    else:
        create_pbar('Removing %s orphaned m arches:' % mlen, mlen)
        for i, m in enumerate(marches):
            a = MachineArchitecture.objects.get(name=m.name)
            a.delete()
            update_pbar(i + 1)


def clean_package_names():
    """ Removes package names that are no longer in use
    """

    names = PackageName.objects.filter(package__isnull=True)
    nlen = names.count()

    if nlen == 0:
        if verbose:
            print 'No orphaned package names found.'
    else:
        create_pbar('Removing %s unused package names:' % nlen, nlen)
        for i, packagename in enumerate(names):
            packagename.delete()
            update_pbar(i + 1)


def clean_repos():
    """ Removes repositories that contain no mirrors
    """

    repos = Repository.objects.filter(mirror__isnull=True)
    rlen = repos.count()

    if rlen == 0:
        if verbose:
            print 'No repositories with zero mirrors found.'
    else:
        create_pbar('Removing %s empty repos:' % rlen, rlen)
        for i, repo in enumerate(repos):
            repo.delete()
            update_pbar(i + 1)


def clean_reports(s_host=None):
    """ Delete old reports for all hosts, specify host for a single host.
        Reports with non existent hosts are only removed when no host is
        specified.
    """

    hosts = get_hosts(s_host, 'Cleaning reports')
    timestamp = date.today()

    for host in hosts:
        if verbose:
            print host
        host.clean_reports(timestamp)

    if s_host is None:

        reports = Report.objects.filter(accessed__lt=timestamp)
        rlen = reports.count()

        if rlen != 0:
            create_pbar('Removing %s extraneous reports:' % rlen, rlen)
            for i, report in enumerate(reports):
                report.delete()
                update_pbar(i + 1)


def clean_tags():
    """ Delete unused tags
    """

    tagged_items = list(TaggedItem.objects.all())
    to_delete = []

    for t in tagged_items:
        hostid = t.object_id
        try:
            # tags are only used for hosts for now
            Host.objects.get(pk=hostid)
        except ObjectDoesNotExist:
            to_delete.append(t)

    tlen = len(to_delete)

    if tlen != 0:
        create_pbar('Removing %s unused tagged items' % tlen, tlen)
        for i, t in enumerate(to_delete):
            t.delete()
            update_pbar(i + 1)


def host_updates_alt(host=None):
    """ Find updates for all hosts, specify host for a single host
    """

    updated_hosts = []
    hosts = get_hosts(host, 'Finding updates')
    ts = datetime.now().replace(microsecond=0)
    for host in hosts:
        if verbose:
            print '\n%s' % host
        if host not in updated_hosts:
            host.updated_at = ts
            host.find_updates()
            host.save()

            # only include hosts with the same number of packages
            filtered_hosts = Host.objects.annotate(
                packages_count=Count("packages")).filter(
                    packages_count=host.packages.count())
            # exclude hosts with the current timestamp
            filtered_hosts = filtered_hosts.exclude(updated_at=ts)

            packages = set(host.packages.all())
            repos = set(host.repos.all())
            updates = host.updates.all()

            phosts = []
            for fhost in filtered_hosts:

                frepos = set(fhost.repos.all())
                rdiff = repos.difference(frepos)
                if len(rdiff) != 0:
                    continue

                fpackages = set(fhost.packages.all())
                pdiff = packages.difference(fpackages)
                if len(pdiff) != 0:
                    continue

                phosts.append(fhost)

            for phost in phosts:
                phost.updates.clear()
                phost.updates = updates
                phost.updated_at = ts
                phost.save()
                updated_hosts.append(phost)
                if verbose:
                    print 'Added the same updates to %s' % phost
        else:
            if verbose:
                print 'Updates already added in this run'


def host_updates(host=None):
    """ Find updates for all hosts, specify host for a single host
    """

    hosts = get_hosts(host, 'Finding updates')

    for host in hosts:
        if verbose:
            print '\n%s' % host
        host.find_updates()


def diff_hosts(hosts):
    """ Display the differences between two hosts
    """
    hosts_to_compare = get_hosts(hosts, 'Retrieving info')

    if len(hosts_to_compare) != 2:
        sys.exit(1)

    hostA = hosts_to_compare[0]
    hostB = hosts_to_compare[1]
    packagesA = set(hostA.packages.all())
    packagesB = set(hostB.packages.all())
    reposA = set(hostA.repos.all())
    reposB = set(hostB.repos.all())

    package_diff_AB = packagesA.difference(packagesB)
    package_diff_BA = packagesB.difference(packagesA)
    repo_diff_AB = reposA.difference(reposB)
    repo_diff_BA = reposB.difference(reposA)

    print
    print '+ %s' % hostA.hostname
    print '- %s' % hostB.hostname

    if hostA.os != hostB.os:
        print '\nOperating Systems'
        print '+ %s' % hostA.os
        print '- %s' % hostB.os
    else:
        print '\nNo OS differences'

    if hostA.arch != hostB.arch:
        print '\nArchitecture'
        print '+ %s' % hostA.arch
        print '- %s' % hostB.arch
    else:
        print '\nNo architecture differences'

    if hostA.kernel != hostB.kernel:
        print '\nKernels'
        print '+ %s' % hostA.kernel
        print '- %s' % hostB.kernel
    else:
        print '\nNo kernel differences'

    if len(package_diff_AB) != 0 or len(package_diff_BA) != 0:
        print '\nPackages'
        for package in package_diff_AB:
            print '+ %s' % package
        for package in package_diff_BA:
            print '- %s' % package
    else:
        print '\nNo package differences'

    if len(repo_diff_AB) != 0 or len(repo_diff_BA) != 0:
        print '\nRepositories'
        for repo in repo_diff_AB:
            print '+ %s' % repo
        for repo in repo_diff_BA:
            print '- %s' % repo
    else:
        print '\nNo repo differences'


def dns_checks(host=None):
    """ Check all hosts for reverse DNS mismatches, specify host for a single
        host
    """

    hosts = get_hosts(host, 'Checking rDNS')

    for host in hosts:
        if verbose:
            print '%s:\t' % host.__unicode__()[0:25].ljust(25),
            sys.stdout.softspace = False
        host.check_rdns()


def process_reports(host=None, force=False):
    """ Process all pending reports, specify host to process only a single host
        The --force option forces even processed reports to be reprocessed
        No reports are skipped in case some reports contain repo information
        and others only contain package information.
    """

    reports = []
    if host:
        try:
            reports = Report.objects.filter(
                processed=force, host=host).order_by('created')
            message = 'Processing reports for host %s' % host
        except:
            message = 'No reports exist for host %s' % host
    else:
        message = 'Processing reports for all hosts'
        reports = Report.objects.filter(processed=force).order_by('created')

    if verbose:
        print message

    for report in reports:
        report.process(False)


def clean_updates():
    """ Removes PackageUpdate objects that are no longer
        linked to any hosts
    """

    package_updates = list(PackageUpdate.objects.all())

    for update in package_updates:
        if update.host_set.count() == 0:
            if verbose:
                print 'Removing unused update %s' % update
            update.delete()
        for duplicate in package_updates:
            if update.oldpackage == duplicate.oldpackage and \
                    update.newpackage == duplicate.newpackage and \
                    update.security == duplicate.security and \
                    update.id != duplicate.id:
                if verbose:
                    print "Removing duplicate update: %s" % (update)
                for host in duplicate.host_set.all():
                    host.updates.remove(duplicate)
                    host.updates.add(update)
                    host.save()
                duplicate.delete()


def dbcheck():
    """ Runs all clean_* functions to check database consistency
    """
    clean_updates()
    clean_packages()
    clean_package_names()
    clean_arches()
    clean_repos()
    clean_updates()
    clean_tags()


def collect_args():

    parser = argparse.ArgumentParser(description='Patchman CLI tool')
    parser.add_argument(
        '-f', '--force', action='store_true',
        help='Ignore stored checksums and force-refresh all mirrors')
    parser.add_argument(
        '-q', '--quiet', action='store_true',
        help='Quiet mode (e.g. for cronjobs)')
    parser.add_argument(
        '-r', '--refresh-repos', action='store_true',
        help='Refresh repositories')
    parser.add_argument(
        '-R', '--repo',
        help='Only perform action on a specific repository (repo_id)')
    parser.add_argument(
        '-lr', '--list-repos', action='store_true',
        help='List all repositories')
    parser.add_argument(
        '-lh', '--list-hosts', action='store_true',
        help='List all hosts')
    parser.add_argument(
        '-u', '--host-updates', action='store_true',
        help='Find host updates')
    parser.add_argument(
        '-A', '--host-updates-alt', action='store_true',
        help='Find host updates (alternative algorithm that may be faster \
        when there are many homogeneous hosts)')
    parser.add_argument(
        '-H', '--host',
        help='Only perform action on a specific host (fqdn)')
    parser.add_argument(
        '-p', '--process-reports', action='store_true',
        help='Process pending reports')
    parser.add_argument(
        '-c', '--clean-reports', action='store_true',
        help='Remove all but the last three reports')
    parser.add_argument(
        '-d', '--dbcheck', action='store_true',
        help='Perform some sanity checks and clean unused db entries')
    parser.add_argument(
        '-n', '--dns-checks', action='store_true',
        help='Perform reverse DNS checks if enabled for that host')
    parser.add_argument(
        '-a', '--all', action='store_true',
        help='Convenience flag for -r -A -p -c -d -n')
    parser.add_argument(
        '-D', '--diff', metavar=('hostA', 'hostB'), nargs=2,
        help='Show differences between two hosts in difflike output')
    return parser


def process_args(args):

    showhelp = True
    recheck = False

    if args.all:
        args.process_reports = True
        args.clean_reports = True
        args.refresh_repos = True
        args.host_updates_alt = True
        args.clean_updates = True
        args.dbcheck = True
        args.dns_checks = True
    if args.list_repos:
        list_repos(args.repo)
        return False
    if args.list_hosts:
        list_hosts(args.host)
        return False
    if args.diff:
        diff_hosts(args.diff)
        return False
    if args.clean_reports:
        clean_reports(args.host)
        showhelp = False
    if args.process_reports:
        process_reports(args.host, args.force)
        showhelp = False
    if args.dbcheck:
        dbcheck()
        showhelp = False
    if args.refresh_repos:
        refresh_repos(args.repo, args.force)
        showhelp = False
        recheck = True
    if args.host_updates:
        host_updates(args.host)
        showhelp = False
        recheck = True
    if args.host_updates_alt:
        host_updates_alt(args.host)
        showhelp = False
        recheck = True
    if args.dbcheck and recheck:
        dbcheck()
    if args.dns_checks:
        dns_checks(args.host)
        showhelp = False
    return showhelp


def main():

    global verbose
    parser = collect_args()
    args = parser.parse_args()

    verbose = not args.quiet
    set_verbosity(verbose)

    showhelp = process_args(args)

    if showhelp:
        parser.print_help()

if __name__ == '__main__':
    main()
