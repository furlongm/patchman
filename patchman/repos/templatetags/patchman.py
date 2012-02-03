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

register = template.Library()


@register.simple_tag
def yes_no_button_repo_en(repo):

    if repo.enabled:
        return """<button onclick="repo_endisable(0, """ + str(repo.id) + """, this)"><img src="%simg/admin/icon-yes.gif" alt="Enabled" /></button>""" % settings.MEDIA_URL
    else:
        return """<button onclick="repo_endisable(1, """ + str(repo.id) + """, this)"> <img src="%simg/admin/icon-no.gif" alt="Disabled" /></button>""" % settings.MEDIA_URL


@register.simple_tag
def yes_no_button_repo_sec(repo):

    if repo.security:
        return """<button onclick="repo_endisablesec(0, """ + str(repo.id) + """, this)"><img src="%simg/admin/icon-yes.gif" alt="Security" /></button>""" % settings.MEDIA_URL
    else:
        return """<button onclick="repo_endisablesec(1, """ + str(repo.id) + """, this)"> <img src="%simg/admin/icon-no.gif" alt="Non-Security" /></button>""" % settings.MEDIA_URL
