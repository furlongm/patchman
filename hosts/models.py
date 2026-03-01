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

from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

try:
    from version_utils.rpm import labelCompare
except ImportError:
    from rpm import labelCompare

from taggit.managers import TaggableManager

from arch.models import MachineArchitecture
from domains.models import Domain
from errata.models import Erratum
from hosts.utils import update_rdns
from modules.models import Module
from operatingsystems.models import OSVariant
from packages.models import Package, PackageUpdate
from packages.utils import get_or_create_package_update
from repos.models import Repository
from repos.utils import find_best_repo
from util.logging import info_message


class Host(models.Model):

    hostname = models.CharField(max_length=255, unique=True)
    ipaddress = models.GenericIPAddressField()
    reversedns = models.CharField(max_length=255, blank=True, null=True)
    check_dns = models.BooleanField(default=False)
    osvariant = models.ForeignKey(OSVariant, on_delete=models.CASCADE)
    kernel = models.CharField(max_length=255)
    arch = models.ForeignKey(MachineArchitecture, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    lastreport = models.DateTimeField()
    packages = models.ManyToManyField(Package, blank=True)
    repos = models.ManyToManyField(Repository, blank=True, through='HostRepo')
    modules = models.ManyToManyField(Module, blank=True)
    updates = models.ManyToManyField(PackageUpdate, blank=True)
    reboot_required = models.BooleanField(default=False)
    host_repos_only = models.BooleanField(default=True)
    tags = TaggableManager(blank=True)
    updated_at = models.DateTimeField(default=timezone.now)
    errata = models.ManyToManyField(Erratum, blank=True)
    # Cached count fields for query optimization
    sec_updates_count = models.PositiveIntegerField(default=0, db_index=True)
    bug_updates_count = models.PositiveIntegerField(default=0, db_index=True)
    packages_count = models.PositiveIntegerField(default=0, db_index=True)
    errata_count = models.PositiveIntegerField(default=0, db_index=True)

    from hosts.managers import HostManager
    objects = HostManager()

    class Meta:
        verbose_name = 'Host'
        verbose_name_plural = 'Hosts'
        ordering = ['hostname']

    def __str__(self):
        return self.hostname

    def show(self):
        """ Show info about this host
        """
        text = f'{self}:\n'
        text += f'IP address   : {self.ipaddress}\n'
        text += f'Reverse DNS  : {self.reversedns}\n'
        text += f'Domain       : {self.domain}\n'
        text += f'OS Variant   : {self.osvariant}\n'
        text += f'Kernel       : {self.kernel}\n'
        text += f'Architecture : {self.arch}\n'
        text += f'Last report  : {self.lastreport}\n'
        text += f'Packages     : {self.get_num_packages()}\n'
        text += f'Repos        : {self.get_num_repos()}\n'
        text += f'Updates      : {self.get_num_updates()}\n'
        text += f'Tags         : {" ".join(self.tags.names())}\n'
        text += f'Needs reboot : {self.reboot_required}\n'
        text += f'Updated at   : {self.updated_at}\n'
        text += f'Host repos   : {self.host_repos_only}\n'

        info_message(text=text)

    def get_absolute_url(self):
        return reverse('hosts:host_detail', args=[self.hostname])

    def get_num_security_updates(self):
        return self.sec_updates_count

    def get_num_bugfix_updates(self):
        return self.bug_updates_count

    def get_num_updates(self):
        return self.sec_updates_count + self.bug_updates_count

    def get_num_packages(self):
        return self.packages_count

    def get_num_repos(self):
        return self.repos.count()

    def get_num_errata(self):
        return self.errata_count

    def check_rdns(self):
        if self.check_dns:
            update_rdns(self)
            if self.hostname.lower() == self.reversedns.lower():
                info_message(text='Reverse DNS matches')
            else:
                text = 'Reverse DNS mismatch found: '
                text += f'{self.hostname} != {self.reversedns}'
                info_message(text=text)
        else:
            info_message(text='Reverse DNS check disabled')

    def clean_reports(self):
        """ Remove all but the last 3 reports for a host
        """
        from reports.models import Report
        reports = list(Report.objects.filter(host=self).order_by('-created')[3:])
        rlen = len(reports)
        for report in reports:
            report.delete()
        if rlen > 0:
            info_message(text=f'{self.hostname}: removed {rlen} old reports')

    def get_host_repo_packages(self):
        if self.host_repos_only:
            hostrepos_q = Q(mirror__repo__in=self.repos.all(),
                            mirror__enabled=True,
                            mirror__repo__enabled=True,
                            mirror__repo__hostrepo__enabled=True)
        else:
            hostrepos_q = \
                Q(mirror__repo__osrelease__osvariant__host=self,
                  mirror__repo__arch=self.arch,
                  mirror__enabled=True,
                  mirror__repo__enabled=True) | \
                Q(mirror__repo__in=self.repos.all(),
                  mirror__enabled=True,
                  mirror__repo__enabled=True)
        return Package.objects.select_related('name', 'arch').filter(hostrepos_q).distinct()

    def process_update(self, package, highest_package):
        if self.host_repos_only:
            host_repos = Q(repo__host=self)
        else:
            host_repos = Q(repo__osrelease__osvariant__host=self, repo__arch=self.arch) | Q(repo__host=self)
        mirrors = highest_package.mirror_set.filter(host_repos).select_related('repo')
        security = False
        # if any of the containing repos are security, mark the update as a security update
        for mirror in mirrors:
            if mirror.repo.security:
                security = True
        update = get_or_create_package_update(oldpackage=package, newpackage=highest_package, security=security)
        self.updates.add(update)
        info_message(text=f'{update}')
        return update.id

    def find_updates(self):

        kernels_q = Q(name__name='kernel') | \
            Q(name__name__startswith='kernel-') | \
            Q(name__name__startswith='virtualbox-kmp-') | \
            Q(name__name__startswith='linux-image-') | \
            Q(name__name__startswith='linux-headers-') | \
            Q(name__name__regex=r'^linux-modules-\d') | \
            Q(name__name__regex=r'^linux-modules-extra-\d') | \
            Q(name__name__startswith='linux-tools-') | \
            Q(name__name__startswith='linux-cloud-tools-') | \
            Q(name__name__startswith='linux-kbuild-') | \
            Q(name__name__startswith='linux-support-') | \
            Q(name__name='linux') | \
            Q(name__name='linux-lts') | \
            Q(name__name='linux-zen') | \
            Q(name__name='linux-hardened') | \
            Q(name__name='linux-rt') | \
            Q(name__name='linux-rt-lts') | \
            Q(name__name='linux-headers') | \
            Q(name__name='linux-lts-headers') | \
            Q(name__name='linux-zen-headers') | \
            Q(name__name='linux-hardened-headers') | \
            Q(name__name='linux-rt-headers') | \
            Q(name__name='linux-rt-lts-headers')
        repo_packages = self.get_host_repo_packages()
        host_packages = self.packages.exclude(kernels_q).distinct()
        kernel_packages = self.packages.filter(kernels_q)

        if self.host_repos_only:
            update_ids = self.find_host_repo_updates(host_packages, repo_packages)
        else:
            update_ids = self.find_osrelease_repo_updates(host_packages, repo_packages)

        kernel_update_ids = self.find_kernel_updates(kernel_packages, repo_packages)
        for ku_id in kernel_update_ids:
            update_ids.append(ku_id)

        for update in self.updates.all():
            if update.id not in update_ids:
                self.updates.remove(update)

    def find_host_repo_updates(self, host_packages, repo_packages):

        update_ids = []
        hostrepos_q = Q(repo__mirror__enabled=True,
                        repo__mirror__refresh=True,
                        repo__mirror__repo__enabled=True,
                        host=self)
        hostrepos = HostRepo.objects.select_related('host', 'repo').filter(hostrepos_q)

        for package in host_packages:
            highest_package = package
            best_repo = find_best_repo(package, hostrepos)
            priority = None
            if best_repo is not None:
                priority = best_repo.priority

            # find the packages that are potential updates
            pu_q = Q(
                name=package.name,
                arch=package.arch,
                packagetype=package.packagetype,
                category=package.category,
            )
            potential_updates = repo_packages.filter(pu_q).exclude(version__startswith='9999')
            for pu in potential_updates:
                pu_is_module_package = False
                pu_in_enabled_modules = False
                if pu.module_set.exists():
                    pu_is_module_package = True
                    for module in pu.module_set.all():
                        if module in self.modules.all():
                            pu_in_enabled_modules = True
                if pu_is_module_package:
                    if not pu_in_enabled_modules:
                        continue
                if package.compare_version(pu) == -1:
                    # package updates that are fixed by erratum (may already be superceded by another update)
                    errata = pu.provides_fix_in_erratum.all()
                    if errata:
                        for erratum in errata:
                            self.errata.add(erratum)
                    if highest_package.compare_version(pu) == -1:
                        if priority is not None:
                            # proceed only if the package is from a repo with a
                            # priority and that priority is >= the repo priority
                            pu_best_repo = find_best_repo(pu, hostrepos)
                            if pu_best_repo:
                                pu_priority = pu_best_repo.priority
                                if pu_priority >= priority:
                                    highest_package = pu
                        else:
                            highest_package = pu

            if highest_package != package:
                uid = self.process_update(package, highest_package)
                if uid is not None:
                    update_ids.append(uid)
        return update_ids

    def find_osrelease_repo_updates(self, host_packages, repo_packages):

        update_ids = []
        for package in host_packages:
            highest_package = package

            # find the packages that are potential updates
            pu_q = Q(name=package.name,
                     arch=package.arch,
                     packagetype=package.packagetype)
            potential_updates = repo_packages.filter(pu_q)
            for pu in potential_updates:
                pu_is_module_package = False
                pu_in_enabled_modules = False
                if pu.module_set.exists():
                    pu_is_module_package = True
                    for module in pu.module_set.all():
                        if module in self.modules.all():
                            pu_in_enabled_modules = True
                if pu_is_module_package:
                    if not pu_in_enabled_modules:
                        continue
                if package.compare_version(pu) == -1:
                    # package updates that are fixed by erratum (may already be superceded by another update)
                    errata = pu.provides_fix_in_erratum.all()
                    if errata:
                        for erratum in errata:
                            self.errata.add(erratum)
                    if highest_package.compare_version(pu) == -1:
                        highest_package = pu

            if highest_package != package:
                uid = self.process_update(package, highest_package)
                if uid is not None:
                    update_ids.append(uid)
        return update_ids

    def check_if_reboot_required(self, host_highest):
        """Check if a reboot is required (running kernel < installed highest).

        Uses labelCompare for RPM-style version tuples parsed from uname -r.
        Only valid for RPM kernels — DEB and Arch use compare_version via
        their respective find_*_kernel_updates methods.
        """
        parts = self.kernel.split('-')
        if len(parts) < 2:
            return
        ver, rel = parts[:2]
        # strip arch suffix from uname -r release (e.g. '.x86_64', '.aarch64')
        arch_suffix = '.' + self.arch.name
        if rel.endswith(arch_suffix):
            rel = rel[:-len(arch_suffix)]
        # SUSE uname -r truncates the micro release (e.g. '160000.8' vs
        # RPM release '160000.8.1'), so check for prefix match first
        if host_highest.version == ver and \
                (host_highest.release == rel or
                 host_highest.release.startswith(rel + '.')):
            self.reboot_required = False
            return
        kernel_ver = ('', str(ver), str(rel))
        host_highest_ver = ('', host_highest.version, host_highest.release)
        if labelCompare(kernel_ver, host_highest_ver) == -1:
            self.reboot_required = True
        else:
            self.reboot_required = False

    def _get_deb_kernel_flavour(self, pkg_name):
        """Extract the flavour suffix from a DEB kernel package name.

        e.g. 'linux-image-6.8.0-51-generic' → 'generic'
             'linux-image-6.8.0-51-lowlatency' → 'lowlatency'
             'linux-image-6.1.0-28-cloud-amd64' → 'cloud-amd64'
             'linux-modules-extra-6.8.0-51-generic' → 'generic'
        Returns None if the flavour cannot be determined.
        """
        for prefix in self._deb_kernel_prefixes:
            if pkg_name.startswith(prefix):
                # strip prefix, then split version from flavour
                # e.g. '6.8.0-51-generic' or '6.1.0-28-cloud-amd64'
                remainder = pkg_name[len(prefix):]
                # version parts are numeric/dotted, flavour starts after
                # e.g. '6.8.0-51-generic' → parts=['6.8.0', '51', 'generic']
                parts = remainder.split('-')
                # find first non-numeric part (not starting with digit)
                for i, part in enumerate(parts):
                    if part and not part[0].isdigit():
                        return '-'.join(parts[i:])
                return None
        return None

    def _get_running_kernel_flavour(self):
        """Extract the flavour from the running kernel string.

        e.g. '6.8.0-51-generic' → 'generic'
             '6.8.0-51-lowlatency' → 'lowlatency'
             '6.1.0-28-cloud-amd64' → 'cloud-amd64'
        Returns None for RPM-style kernels (no flavour suffix).
        """
        parts = self.kernel.split('-')
        if len(parts) >= 2:
            # find first non-numeric part after the version
            for i, part in enumerate(parts):
                if i > 0 and part and not part[0].isdigit():
                    return '-'.join(parts[i:])
        return None

    # longest prefixes first to avoid linux-modules- matching linux-modules-extra-
    _deb_kernel_prefixes = [
        'linux-image-unsigned-',
        'linux-modules-extra-',
        'linux-cloud-tools-',
        'linux-image-uc-',
        'linux-image-',
        'linux-headers-',
        'linux-modules-',
        'linux-support-',
        'linux-kbuild-',
        'linux-tools-',
    ]

    def find_kernel_updates(self, kernel_packages, repo_packages):

        update_ids = []
        self.reboot_required = False

        # build hostrepos for priority filtering (same as find_host_repo_updates)
        hostrepos = None
        if self.host_repos_only:
            hostrepos_q = Q(repo__mirror__enabled=True,
                            repo__mirror__refresh=True,
                            repo__mirror__repo__enabled=True,
                            host=self)
            hostrepos = HostRepo.objects.select_related(
                'host', 'repo').filter(hostrepos_q)

        deb_kernels = kernel_packages.filter(packagetype='D')
        rpm_kernels = kernel_packages.filter(packagetype='R')
        arch_kernels = kernel_packages.filter(packagetype='A')

        update_ids.extend(self._find_rpm_kernel_updates(rpm_kernels, repo_packages, hostrepos))
        update_ids.extend(self._find_deb_kernel_updates(deb_kernels, repo_packages, hostrepos))
        update_ids.extend(self._find_arch_kernel_updates(arch_kernels, repo_packages, hostrepos))

        self.save(update_fields=['reboot_required'])
        return update_ids

    def _find_rpm_kernel_updates(self, kernel_packages, repo_packages, hostrepos):

        update_ids = []

        # parse running kernel version for comparison
        parts = self.kernel.split('-')
        if len(parts) < 2:
            return update_ids
        ver, rel = parts[:2]
        # strip arch suffix from uname -r release (e.g. '.x86_64')
        arch_suffix = '.' + self.arch.name
        if rel.endswith(arch_suffix):
            rel = rel[:-len(arch_suffix)]

        # deduplicate: only process each kernel package name once
        processed_names = set()

        for package in kernel_packages:
            if package.name_id in processed_names:
                continue
            processed_names.add(package.name_id)

            pu_q = Q(name=package.name)

            # determine baseline priority from the installed package's repo
            priority = None
            if hostrepos is not None:
                best_repo = find_best_repo(package, hostrepos)
                if best_repo is not None:
                    priority = best_repo.priority

            # find repo highest for this kernel name, respecting priority
            repo_highest = None
            for pu in repo_packages.filter(pu_q):
                if priority is not None:
                    pu_best_repo = find_best_repo(pu, hostrepos)
                    if not pu_best_repo or pu_best_repo.priority < priority:
                        continue
                if repo_highest is None or repo_highest.compare_version(pu) == -1:
                    repo_highest = pu

            if repo_highest is None:
                continue

            # find host highest installed for reboot check
            host_highest = None
            running_package = None
            for hp in self.packages.filter(pu_q):
                if host_highest is None or host_highest.compare_version(hp) == -1:
                    host_highest = hp
                # match installed package to running kernel
                # SUSE uname -r truncates micro release ('160000.8' vs
                # RPM '160000.8.1') so use prefix match with dot boundary
                if hp.version == ver and \
                        (hp.release == rel or
                         hp.release.startswith(rel + '.')):
                    running_package = hp

            # for the running kernel's flavour, compare running vs repo
            # for other flavours, compare highest installed vs repo
            if running_package:
                base_package = running_package
            else:
                base_package = host_highest

            if base_package and base_package.compare_version(repo_highest) == -1:
                uid = self.process_update(base_package, repo_highest)
                if uid is not None:
                    update_ids.append(uid)

            # reboot check only on primary kernel packages
            if host_highest and package.name.name in (
                'kernel', 'kernel-core', 'kernel-debug-core',
                'kernel-default', 'kernel-rt', 'kernel-azure',
                'kernel-kvmsmall',
                'kernel-uek', 'kernel-uki-virt', 'kernel-debug-uki-virt',
            ):
                self.check_if_reboot_required(host_highest)

        return update_ids

    def _find_arch_kernel_updates(self, kernel_packages, repo_packages, hostrepos):

        update_ids = []

        for package in kernel_packages:
            pu_q = Q(name=package.name)

            # determine baseline priority from the installed package's repo
            priority = None
            if hostrepos is not None:
                best_repo = find_best_repo(package, hostrepos)
                if best_repo is not None:
                    priority = best_repo.priority

            repo_highest = None
            for rp in repo_packages.filter(pu_q):
                if priority is not None:
                    rp_best_repo = find_best_repo(rp, hostrepos)
                    if not rp_best_repo or rp_best_repo.priority < priority:
                        continue
                if repo_highest is None or repo_highest.compare_version(rp) == -1:
                    repo_highest = rp

            if repo_highest is None:
                continue

            if package.compare_version(repo_highest) == -1:
                uid = self.process_update(package, repo_highest)
                if uid is not None:
                    update_ids.append(uid)

            # reboot check for main kernel packages (not -headers)
            # Arch uname -r format varies by flavour:
            #   linux:     6.12.8-arch1-1         (pkgver=6.12.8.arch1)
            #   linux-lts: 6.1.68-1-lts           (pkgver=6.1.68)
            #   linux-zen: 6.12.8-zen1-1-zen      (pkgver=6.12.8.zen1)
            # The only reliable common part is the base version (first segment
            # of uname -r) which maps to the numeric prefix of pkgver
            if package.name.name in (
                'linux', 'linux-lts', 'linux-zen', 'linux-hardened',
                'linux-rt', 'linux-rt-lts',
            ):
                running_base = self.kernel.split('-')[0] if self.kernel else ''
                pkg_ver = package.version
                # pkgver is either 'X.Y.Z' (lts) or 'X.Y.Z.flavourN' (others)
                # check if the package version matches or extends the base
                if pkg_ver != running_base and not pkg_ver.startswith(running_base + '.'):
                    self.reboot_required = True

        return update_ids

    def _find_deb_kernel_updates(self, kernel_packages, repo_packages, hostrepos):

        update_ids = []
        running_flavour = self._get_running_kernel_flavour()

        # find the linux-image package matching the running kernel
        running_kernel_pkg = None
        for package in kernel_packages:
            pkg_name = package.name.name
            if pkg_name.startswith('linux-image-') and pkg_name.endswith(self.kernel):
                running_kernel_pkg = package
                break

        # determine baseline priority from the running kernel's repo
        priority = None
        if hostrepos is not None and running_kernel_pkg is not None:
            best_repo = find_best_repo(running_kernel_pkg, hostrepos)
            if best_repo is not None:
                priority = best_repo.priority

        processed_prefixes = set()
        for package in kernel_packages:
            pkg_name = package.name.name
            flavour = self._get_deb_kernel_flavour(pkg_name)

            # if we know the running flavour, only process matching packages
            # if we don't (unflavoured kernel), process all kernel packages
            if running_flavour and flavour != running_flavour:
                continue

            # determine the prefix (e.g. 'linux-image-')
            prefix = None
            for p in self._deb_kernel_prefixes:
                if pkg_name.startswith(p):
                    prefix = p
                    break
            if prefix is None or prefix in processed_prefixes:
                continue
            processed_prefixes.add(prefix)

            # build endswith filter for flavoured kernels
            name_filter = Q(
                name__name__startswith=prefix,
                packagetype='D',
            )
            if running_flavour:
                name_filter &= Q(name__name__endswith=f'-{running_flavour}')

            # find repo highest for this prefix+flavour, respecting priority
            repo_highest = None
            for rp in repo_packages.filter(name_filter):
                if priority is not None:
                    rp_best_repo = find_best_repo(rp, hostrepos)
                    if not rp_best_repo or rp_best_repo.priority < priority:
                        continue
                if repo_highest is None or repo_highest.compare_version(rp) == -1:
                    repo_highest = rp

            if repo_highest is None:
                continue

            # find the installed package matching the running kernel for this prefix
            base_package = None
            expected_name = prefix + self.kernel
            for hp in self.packages.filter(name_filter):
                if hp.name.name == expected_name:
                    base_package = hp
                    break

            # fallback: if no running match, use the installed package we started with
            if base_package is None:
                base_package = package

            if base_package.compare_version(repo_highest) == -1:
                uid = self.process_update(base_package, repo_highest)
                if uid is not None:
                    update_ids.append(uid)

        # reboot check: see if a newer linux-image is installed but not running
        # use compare_version (DEB semantics) instead of labelCompare
        if running_kernel_pkg:
            for package in kernel_packages:
                if package.name.name.startswith('linux-image-'):
                    flavour = self._get_deb_kernel_flavour(package.name.name)
                    if running_flavour is None or flavour == running_flavour:
                        if running_kernel_pkg.compare_version(package) == -1:
                            self.reboot_required = True
                            break

        return update_ids


class HostRepo(models.Model):
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    class Meta:
        unique_together = ['host', 'repo']
        ordering = ['host', 'repo']

    def __str__(self):
        return f'{self.host}-{self.repo}'
