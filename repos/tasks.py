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

from celery import shared_task
from django.core.cache import cache

from repos.models import Repository
from util.logging import warning_message


@shared_task
def refresh_repo(repo_id, force=False):
    """ Refresh metadata for a single repo
    """
    repo = Repository.objects.get(id=repo_id)
    repo.refresh(force)


@shared_task
def refresh_repos(force=False):
    """ Refresh metadata for all enabled repos
    """
    repos = Repository.objects.filter(enabled=True)
    lock_key = 'refresh_repos_lock'
    # lock will expire after 1 day
    lock_expire = 60 * 60 * 24

    if cache.add(lock_key, 'true', lock_expire):
        try:
            for repo in repos:
                refresh_repo.delay(repo.id, force)
        finally:
            cache.delete(lock_key)
    else:
        warning_message('Already refreshing repos, skipping task.')
