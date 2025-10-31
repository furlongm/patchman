# Copyright 2016-2025 Marcus Furlong <furlongm@gmail.com>
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

from django.template import Library
from django.templatetags.static import static
from django.utils import timezone
from django.utils.html import format_html

from util import get_setting_of_type

register = Library()


@register.simple_tag
def report_alert(lastreport):
    html = ''
    alert_icon = static('img/icon-alert.gif')
    days = get_setting_of_type(
        setting_name='DAYS_WITHOUT_REPORT',
        setting_type=int,
        default=14,
    )
    if lastreport < (timezone.now() - timedelta(days=days)):
        html = f'<img src="{alert_icon}" alt="Outdated Report" />'
    return format_html(html)
