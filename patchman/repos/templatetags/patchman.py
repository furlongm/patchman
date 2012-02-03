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
