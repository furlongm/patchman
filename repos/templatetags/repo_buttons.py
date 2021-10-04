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

from django.template import Library
from django.templatetags.static import static
from django.utils.html import format_html

register = Library()


@register.simple_tag
def yes_no_button_repo_en(repo):

    repo_url = repo.get_absolute_url()
    yes_icon = static('img/icon-yes.gif')
    no_icon = static('img/icon-no.gif')
    html = '<button onclick="repo_toggle_enabled'
    html += '(\'{0!s}\', this, event)">'.format(repo_url)
    if repo.enabled:
        html += '<img src="{0!s}" alt="Enabled" />'.format(yes_icon)
    else:
        html += '<img src="{0!s}" alt="Disabled" />'.format(no_icon)
    html += '</button>'
    return format_html(html)


@register.simple_tag
def yes_no_button_repo_sec(repo):

    repo_url = repo.get_absolute_url()
    yes_icon = static('img/icon-yes.gif')
    no_icon = static('img/icon-no.gif')
    html = '<button onclick="repo_toggle_security'
    html += '(\'{0!s}\', this, event)">'.format(repo_url)
    if repo.security:
        html += '<img src="{0!s}" alt="Security" />'.format(yes_icon)
    else:
        html += '<img src="{0!s}" alt="Non-Security" />'.format(no_icon)
    html += '</button>'
    return format_html(html)
