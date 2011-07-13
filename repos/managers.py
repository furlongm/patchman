from django.db import models

class RepositoryManager(models.Manager):
    def get_query_set(self):
        return super(RepositoryManager, self).get_query_set().select_related()
