# Copyright 2012 VPAC, http://www.vpac.org
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
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.html import format_html

register = Library()


@register.simple_tag
def yes_no_button_repo_en(repo):

    repo_url = repo.get_absolute_url()
    yes_icon = static('img/icon-yes.gif')
    no_icon = static('img/icon-no.gif')
    if repo.enabled:
        html = '<button onclick="repo_toggle_enabled(\'%s\', this, event)">' \
               '<img src="%s" alt="Enabled" /></button>' \
               % (repo_url, yes_icon)
    else:
        html = '<button onclick="repo_toggle_enabled(\'%s\', this, event)">' \
               '<img src="%s" alt="Disabled" /></button>' \
               % (repo_url, no_icon)
    return format_html(html)


@register.simple_tag
def yes_no_button_repo_sec(repo):

    repo_url = repo.get_absolute_url()
    yes_icon = static('img/icon-yes.gif')
    no_icon = static('img/icon-no.gif')
    if repo.security:
        html = '<button onclick="repo_toggle_security(\'%s\', this, event)">' \
               '<img src="%s" alt="Security" /></button>' \
               % (repo_url, yes_icon)
    else:
        html = '<button onclick="repo_toggle_security(\'%s\', this, event)">' \
               '<img src="%s" alt="Non-Security" /></button>' \
               % (repo_url, no_icon)
    return format_html(html)
