from django.db import models

from patchman.arch.models import MachineArchitecture
from patchman.packages.models import Package
from patchman.repos.managers import RepositoryManager

class Repository(models.Model):

    RPM = 'R'
    DEB = 'D'

    REPO_TYPES = (
        (RPM, 'rpm'),
        (DEB, 'deb'),
    )

    name = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    arch = models.ForeignKey(MachineArchitecture)
    security = models.BooleanField()
    repotype = models.CharField(max_length=1, choices=REPO_TYPES)
    enabled = models.BooleanField()
    last_access_ok = models.BooleanField()
    file_checksum = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField()
    packages = models.ManyToManyField(Package)

    class Meta:
        verbose_name_plural = "Repositories"

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('repo_detail', [self.id])
