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

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.db.models import F
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from patchman.hosts.models import Host
from patchman.operatingsystems.models import OSRelease, OSVariant
from patchman.packages.models import Package
from patchman.reports.models import Report
from patchman.repos.models import Mirror, Repository
from patchman.util import get_setting_of_type
from patchman.util.models import ClientCertificate, EnrollmentToken
from patchman.util.pki import PKIError, get_pki_provider
from patchman.util.serializers import (
    EnrollRequestSerializer, EnrollResponseSerializer,
    RenewRequestSerializer, RenewResponseSerializer,
)

logger = logging.getLogger(__name__)


class EnrollView(APIView):
    """Exchange enrollment token for signed certificate."""

    permission_classes = [AllowAny]  # Token is the auth

    def post(self, request):
        serializer = EnrollRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token_str = serializer.validated_data['token']
        csr_pem = serializer.validated_data['csr']
        hostname = serializer.validated_data['hostname']

        # Check if PKI provider is configured
        provider = get_pki_provider()
        if not provider:
            return Response(
                {'error': 'Certificate enrollment not configured on this server'},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        if not provider.is_available():
            return Response(
                {'error': 'PKI provider is not available'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Validate token
        try:
            token = EnrollmentToken.objects.get(token=token_str)
        except EnrollmentToken.DoesNotExist:
            logger.warning(f'Invalid enrollment token attempted for {hostname}')
            return Response(
                {'error': 'Invalid enrollment token'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not token.is_valid:
            logger.warning(f'Expired/used token attempted for {hostname}')
            return Response(
                {'error': 'Token expired or already used'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not token.matches_hostname(hostname):
            logger.warning(
                f'Hostname {hostname} not allowed for token {token.token[:20]}...'
            )
            return Response(
                {'error': f'Hostname {hostname} not allowed for this token'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate CSR
        csr_valid, csr_error = self._validate_csr(csr_pem, hostname)
        if not csr_valid:
            return Response(
                {'error': csr_error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Sign CSR
        validity_days = getattr(settings, 'CERT_VALIDITY_DAYS', 365)
        try:
            cert_pem, serial = provider.sign_csr(csr_pem, hostname, validity_days)
        except PKIError as e:
            logger.error(f'Certificate signing failed for {hostname}: {e}')
            return Response(
                {'error': f'Certificate signing failed: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Record certificate
        ClientCertificate.objects.create(
            hostname=hostname,
            serial_number=serial,
            expires_at=timezone.now() + timedelta(days=validity_days),
            enrollment_token=token,
        )

        # Mark token as used
        if token.single_use:
            token.mark_used(hostname)

        logger.info(f'Issued certificate for {hostname} (serial: {serial})')

        response_data = {
            'certificate': cert_pem,
            'serial_number': serial,
            'expires_in_days': validity_days,
        }
        return Response(EnrollResponseSerializer(response_data).data)

    def _validate_csr(self, csr_pem, hostname):
        """Validate CSR format and CN."""
        try:
            from cryptography import x509
            csr = x509.load_pem_x509_csr(csr_pem.encode())

            # Verify CSR CN matches requested hostname
            cn_attrs = csr.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
            if cn_attrs and cn_attrs[0].value != hostname:
                return False, 'CSR common name does not match hostname'

            return True, None

        except ImportError:
            # cryptography not available, skip validation
            logger.warning('cryptography not available, skipping CSR validation')
            return True, None
        except Exception as e:
            return False, f'Invalid CSR: {e}'


class RenewView(APIView):
    """Renew client certificate using existing cert for auth."""

    permission_classes = [AllowAny]  # Existing cert is the auth

    def post(self, request):
        # Must have valid client cert
        if not getattr(request, 'client_cert_verified', False):
            return Response(
                {'error': 'Valid client certificate required for renewal'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        hostname = getattr(request, 'client_cert_cn', '')
        if not hostname:
            return Response(
                {'error': 'Client certificate CN not found'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = RenewRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        csr_pem = serializer.validated_data['csr']

        # Check if PKI provider is configured
        provider = get_pki_provider()
        if not provider:
            return Response(
                {'error': 'Certificate enrollment not configured on this server'},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        if not provider.is_available():
            return Response(
                {'error': 'PKI provider is not available'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Validate CSR CN matches current cert CN
        csr_valid, csr_error = self._validate_csr(csr_pem, hostname)
        if not csr_valid:
            return Response(
                {'error': csr_error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Sign CSR
        validity_days = getattr(settings, 'CERT_VALIDITY_DAYS', 365)
        try:
            cert_pem, serial = provider.sign_csr(csr_pem, hostname, validity_days)
        except PKIError as e:
            logger.error(f'Certificate renewal failed for {hostname}: {e}')
            return Response(
                {'error': f'Certificate signing failed: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Record new certificate
        ClientCertificate.objects.create(
            hostname=hostname,
            serial_number=serial,
            expires_at=timezone.now() + timedelta(days=validity_days),
        )

        logger.info(f'Renewed certificate for {hostname} (serial: {serial})')

        response_data = {
            'certificate': cert_pem,
            'serial_number': serial,
            'expires_in_days': validity_days,
        }
        return Response(RenewResponseSerializer(response_data).data)

    def _validate_csr(self, csr_pem, hostname):
        """Validate CSR format and CN."""
        try:
            from cryptography import x509
            csr = x509.load_pem_x509_csr(csr_pem.encode())

            cn_attrs = csr.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
            if cn_attrs and cn_attrs[0].value != hostname:
                return False, 'CSR hostname must match current certificate'

            return True, None

        except ImportError:
            logger.warning('cryptography not available, skipping CSR validation')
            return True, None
        except Exception as e:
            return False, f'Invalid CSR: {e}'


@login_required
def dashboard(request):

    try:
        site = Site.objects.get_current()
    except Site.DoesNotExist:
        site = {'name': '', 'domainname': ''}

    return render(request, 'dashboard.html', {'site': site})


@login_required
def issues(request):

    try:
        site = Site.objects.get_current()
    except Site.DoesNotExist:
        site = {'name': '', 'domainname': ''}

    hosts = Host.objects.all()
    repos = Repository.objects.all()

    # host issues
    days = get_setting_of_type(
        setting_name='DAYS_WITHOUT_REPORT',
        setting_type=int,
        default=14,
    )
    last_report_delta = timezone.now() - timedelta(days=days)
    counts = {
        'stale_hosts': hosts.filter(lastreport__lt=last_report_delta).count(),
        'norepo_hosts': hosts.filter(repos__isnull=True, osvariant__osrelease__repos__isnull=True).count(),
        'reboot_hosts': hosts.filter(reboot_required=True).count(),
        'secupdate_hosts': hosts.filter(sec_updates_count__gt=0).count(),
        'bugupdate_hosts': hosts.filter(bug_updates_count__gt=0, sec_updates_count=0).count(),
        'diff_rdns_hosts': hosts.exclude(reversedns=F('hostname')).filter(check_dns=True).count(),
        'noosrelease_osvariants': OSVariant.objects.filter(osrelease__isnull=True).count(),
        'nohost_osvariants': OSVariant.objects.filter(host__isnull=True).count(),
        'norepo_osreleases': 0,
    }

    if hosts.filter(host_repos_only=False).exists():
        counts['norepo_osreleases'] = OSRelease.objects.filter(repos__isnull=True).count()

    # mirror issues — chained .filter() on M2M creates separate JOINs,
    # so this finds repos with BOTH a failing AND a succeeding mirror
    failed_mirrors_qs = repos.filter(auth_required=False).filter(mirror__last_access_ok=False).filter(mirror__last_access_ok=True).distinct()  # noqa
    failed_mirror_ids = list(failed_mirrors_qs.values_list('id', flat=True))
    counts['failed_mirrors'] = len(failed_mirror_ids)
    counts['disabled_mirrors'] = repos.filter(auth_required=False, mirror__enabled=False, mirror__mirrorlist=False).distinct().count()  # noqa
    counts['norefresh_mirrors'] = repos.filter(auth_required=False, mirror__refresh=False).distinct().count()

    # repo issues — all mirrors failing = has failing mirrors but not in partial-failure set
    counts['failed_repos'] = repos.filter(auth_required=False, mirror__last_access_ok=False).exclude(id__in=failed_mirror_ids).distinct().count()  # noqa
    counts['unused_repos'] = repos.filter(host__isnull=True, osrelease__isnull=True).count()
    counts['nomirror_repos'] = repos.filter(mirror__isnull=True).count()
    counts['nohost_repos'] = repos.filter(host__isnull=True).count()

    # package issues
    counts['norepo_packages'] = Package.objects.filter(mirror__isnull=True, oldpackage__isnull=True, host__isnull=False).distinct().count()  # noqa
    counts['orphaned_packages'] = Package.objects.filter(mirror__isnull=True, host__isnull=True).count()

    # report issues
    counts['unprocessed_reports'] = Report.objects.filter(processed=False).count()

    # possible mirrors (checksum duplicates across repos)
    checksums = {}
    possible_mirrors = {}
    for csvalue in Mirror.objects.filter(packages_count__gt=0).values('packages_checksum').distinct():
        checksum = csvalue['packages_checksum']
        if checksum is not None and checksum != 'yast':
            mirrors = list(Mirror.objects.filter(
                packages_checksum=checksum,
                packages_count__gt=0
            ).select_related('repo'))
            if mirrors:
                checksums[checksum] = mirrors

    for checksum in checksums:
        first_mirror = checksums[checksum][0]
        for mirror in checksums[checksum]:
            if mirror.repo != first_mirror.repo and \
                    mirror.repo.arch == first_mirror.repo.arch and \
                    mirror.repo.repotype == first_mirror.repo.repotype:
                possible_mirrors[checksum] = checksums[checksum]
                continue

    has_issues = any(counts.values()) or bool(possible_mirrors)

    return render(
        request,
        'issues.html',
        {'site': site,
         'has_issues': has_issues,
         'possible_mirrors': possible_mirrors,
         **counts})
