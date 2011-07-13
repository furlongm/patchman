from django.db import models

class PackageManager(models.Manager):
    def get_query_set(self):
        return super(PackageManager, self).get_query_set().select_related()


