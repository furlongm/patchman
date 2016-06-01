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

from django import template
from django.conf import settings
from django.utils.html import format_html, escape

register = template.Library()


@register.simple_tag
def yes_no_button_repo_en(repo):

    if repo.enabled:
        return format_html('<button onclick="repo_toggle_enabled(\'' + escape(repo.get_absolute_url()) + '\', this, event)"><img src="{}img/icon-yes.gif" alt="Enabled" /></button>', escape(settings.STATIC_URL))
    else:
        return format_html('<button onclick="repo_toggle_enabled(\'' + escape(repo.get_absolute_url()) + '\', this, event)"><img src="{}img/icon-no.gif" alt="Disabled" /></button>', escape(settings.STATIC_URL))


@register.simple_tag
def yes_no_button_repo_sec(repo):

    if repo.security:
        return format_html('<button onclick="repo_toggle_security(\'' + escape(repo.get_absolute_url()) + '\', this, event)"><img src="{}img/icon-yes.gif" alt="Security" /></button>', escape(settings.STATIC_URL))
    else:
        return format_html('<button onclick="repo_toggle_security(\'' + escape(repo.get_absolute_url()) + '\', this, event)"><img src="{}img/icon-no.gif" alt="Non-Security" /></button>', escape(settings.STATIC_URL))
