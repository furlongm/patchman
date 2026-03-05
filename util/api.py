# Copyright 2025 Marcus Furlong <furlongm@gmail.com>
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

from datetime import timedelta

from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from errata.models import Erratum
from hosts.models import Host
from operatingsystems.models import OSVariant
from repos.models import Mirror
from util import get_setting_of_type


class StatsView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        hosts = Host.objects.all()
        total = hosts.count()

        days = get_setting_of_type(
            setting_name='DAYS_WITHOUT_REPORT',
            setting_type=int,
            default=14,
        )
        stale_cutoff = timezone.now() - timedelta(days=days)

        sec_pending = hosts.filter(sec_updates_count__gt=0).count()
        bug_pending = hosts.filter(
            bug_updates_count__gt=0, sec_updates_count=0,
        ).count()
        reboot = hosts.filter(reboot_required=True).count()
        stale = hosts.filter(lastreport__lt=stale_cutoff).count()
        patched = total - sec_pending - bug_pending

        host_status = {
            'total': total,
            'patched': patched,
            'security_pending': sec_pending,
            'bugfix_pending': bug_pending,
            'reboot_required': reboot,
            'stale': stale,
        }

        # os variant distribution — top 10 + other
        top_n = 10
        os_data = list(
            OSVariant.objects.filter(hosts_count__gt=0)
            .order_by('-hosts_count')
            .values_list('name', 'hosts_count')
        )
        if len(os_data) > top_n:
            os_dist = {
                'labels': [v[0] for v in os_data[:top_n]] + ['Other'],
                'values': [v[1] for v in os_data[:top_n]] + [
                    sum(v[1] for v in os_data[top_n:])
                ],
            }
        else:
            os_dist = {
                'labels': [v[0] for v in os_data],
                'values': [v[1] for v in os_data],
            }

        # kernel version distribution — top 10 + other
        kernel_data = list(
            hosts.exclude(kernel='')
            .values('kernel')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        if len(kernel_data) > top_n:
            kernel_dist = {
                'labels': [k['kernel'] for k in kernel_data[:top_n]] + ['Other'],
                'values': [k['count'] for k in kernel_data[:top_n]] + [
                    sum(k['count'] for k in kernel_data[top_n:])
                ],
            }
        else:
            kernel_dist = {
                'labels': [k['kernel'] for k in kernel_data],
                'values': [k['count'] for k in kernel_data],
            }

        # updates pending by os variant — security + bugfix
        updates_by_os = list(
            OSVariant.objects.filter(hosts_count__gt=0)
            .annotate(
                sec_total=Sum('host__sec_updates_count'),
                bug_total=Sum('host__bug_updates_count'),
            )
            .filter(Q(sec_total__gt=0) | Q(bug_total__gt=0))
            .order_by('-sec_total')
            .values('name', 'sec_total', 'bug_total')
        )
        updates_os = {
            'labels': [u['name'] for u in updates_by_os],
            'security': [u['sec_total'] or 0 for u in updates_by_os],
            'bugfix': [u['bug_total'] or 0 for u in updates_by_os],
        }

        # stale hosts histogram — bucket by reporting age
        now = timezone.now()
        age_buckets = [
            ('< 1 day', now - timedelta(days=1), None),
            ('1-3 days', now - timedelta(days=3), now - timedelta(days=1)),
            ('3-7 days', now - timedelta(days=7), now - timedelta(days=3)),
            ('1-2 weeks', now - timedelta(days=14), now - timedelta(days=7)),
            ('2-4 weeks', now - timedelta(days=28), now - timedelta(days=14)),
            ('> 4 weeks', None, now - timedelta(days=28)),
        ]
        stale_labels = []
        stale_values = []
        for label, lower, upper in age_buckets:
            q = hosts.exclude(lastreport__isnull=True)
            if lower:
                q = q.filter(lastreport__gte=lower)
            if upper:
                q = q.filter(lastreport__lt=upper)
            stale_labels.append(label)
            stale_values.append(q.count())
        stale_histogram = {
            'labels': stale_labels,
            'values': stale_values,
        }

        # reboot pending by os
        reboot_by_os = list(
            OSVariant.objects.filter(hosts_count__gt=0)
            .annotate(
                reboot_count=Count(
                    'host', filter=Q(host__reboot_required=True),
                ),
            )
            .filter(reboot_count__gt=0)
            .order_by('-reboot_count')
            .values('name', 'reboot_count')
        )
        reboot_os = {
            'labels': [r['name'] for r in reboot_by_os],
            'values': [r['reboot_count'] for r in reboot_by_os],
        }

        # top 10 hosts by total pending updates
        top_hosts_updates = list(
            hosts.annotate(
                total_updates=F('sec_updates_count') + F('bug_updates_count'),
            )
            .filter(total_updates__gt=0)
            .order_by('-total_updates')[:top_n]
            .values('hostname', 'sec_updates_count', 'bug_updates_count')
        )
        top_hosts = {
            'labels': [h['hostname'] for h in top_hosts_updates],
            'security': [h['sec_updates_count'] for h in top_hosts_updates],
            'bugfix': [h['bug_updates_count'] for h in top_hosts_updates],
        }

        # top 10 security errata affecting the most hosts
        top_sec_errata = list(
            Erratum.objects.filter(e_type='security', host__isnull=False)
            .annotate(host_count=Count('host', distinct=True))
            .filter(host_count__gt=0)
            .order_by('-host_count')[:top_n]
            .values('name', 'host_count')
        )
        top_errata = {
            'labels': [e['name'] for e in top_sec_errata],
            'values': [e['host_count'] for e in top_sec_errata],
        }

        # mirror/repo health
        mirrors = Mirror.objects.all()
        mirror_total = mirrors.count()
        mirror_ok = mirrors.filter(
            last_access_ok=True, enabled=True,
        ).count()
        mirror_failing = mirrors.filter(last_access_ok=False).count()
        mirror_disabled = mirrors.filter(enabled=False).count()
        mirror_health = {
            'labels': ['OK', 'Failing', 'Disabled'],
            'values': [mirror_ok, mirror_failing, mirror_disabled],
            'total': mirror_total,
        }

        # outstanding errata age histogram
        errata_age_buckets = [
            ('< 1 week', now - timedelta(weeks=1), None),
            ('1-4 weeks', now - timedelta(weeks=4), now - timedelta(weeks=1)),
            ('1-3 months', now - timedelta(days=90), now - timedelta(weeks=4)),
            ('3-6 months', now - timedelta(days=180), now - timedelta(days=90)),
            ('> 6 months', None, now - timedelta(days=180)),
        ]
        errata_age_labels = []
        errata_age_values = []
        active_errata = Erratum.objects.filter(host__isnull=False).distinct()
        for label, lower, upper in errata_age_buckets:
            q = active_errata
            if lower:
                q = q.filter(issue_date__gte=lower)
            if upper:
                q = q.filter(issue_date__lt=upper)
            errata_age_labels.append(label)
            errata_age_values.append(q.count())
        errata_age = {
            'labels': errata_age_labels,
            'values': errata_age_values,
        }

        return Response({
            'host_status': host_status,
            'os_distribution': os_dist,
            'kernel_distribution': kernel_dist,
            'updates_by_os': updates_os,
            'stale_histogram': stale_histogram,
            'reboot_by_os': reboot_os,
            'top_hosts': top_hosts,
            'top_errata': top_errata,
            'mirror_health': mirror_health,
            'errata_age': errata_age,
        })
