from django.db import models

class MachineArchitecture(models.Model):

    name = models.CharField(unique=True, max_length=255)

    class Meta:
        verbose_name = 'Machine Architecture'

    def __unicode__(self):
        return self.name

class PackageArchitecture(models.Model):

    name = models.CharField(unique=True, max_length=255)

    class Meta:
        verbose_name = 'Package Architecture'

    def __unicode__(self):
        return self.name

