from django.db import models
from patchman.repos.models import Repository

class OSGroup(models.Model):

    name = models.CharField(max_length=255)
    repos = models.ManyToManyField(Repository, blank=True, null=True)

    class Meta:
        verbose_name = 'Operating System Group'

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('osgroup_detail', [self.id])

class OS(models.Model):

    name = models.CharField(max_length=255)
# Django 1.3+
#    osgroup = models.ForeignKey(OSGroup, blank=True, null=True, on_delete=models.SET_NULL)
    osgroup = models.ForeignKey(OSGroup, blank=True, null=True)

    class Meta:
        verbose_name = 'Operating System'

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('os_detail', [self.id])
