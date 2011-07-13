from django.db import models

class HostManager(models.Manager):
    def get_query_set(self):
        return super(HostManager, self).get_query_set().select_related()

