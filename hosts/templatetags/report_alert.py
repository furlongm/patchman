# Copyright 2016-2021 Marcus Furlong <furlongm@gmail.com>
#
# This file is part of Patchman.
#
# Patchman is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Patchman is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchman  If not, see <http://www.gnu.org/licenses/>.

from datetime import timedelta

from django.conf import settings

from django.template import Library
from django.utils.html import format_html
from django.templatetags.static import static
from django.utils import timezone

register = Library()


@register.simple_tag
def report_alert(lastreport):
    html = ''
    alert_icon = static('img/icon-alert.gif')
    if hasattr(settings, 'DAYS_WITHOUT_REPORT') and \
            isinstance(settings.DAYS_WITHOUT_REPORT, int):
        days = settings.DAYS_WITHOUT_REPORT
    else:
        days = 14
    if lastreport < (timezone.now() - timedelta(days=days)):
        html = '<img src="{0!s}" alt="Outdated Report" />'.format(alert_icon)
    return format_html(html)
