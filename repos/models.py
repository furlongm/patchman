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
    packages = models.ManyToManyField(Package, blank=True, null=True, through='RepoPackage')

    class Meta:
        verbose_name_plural = "Repositories"

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('repo_detail', [self.id])

    def update(self):
        if self.repotype == Repository.DEB:
            self.update_deb_repo()
        elif repo.repotype == Repository.RPM:
            update_rpm_repo(repo)
        else:
            print 'Error: unknown repo type for repo %s: %s' % (self.id, self.repotype)

class RepoPackage(models.Model):

    repo = models.ForeignKey(Repository)
    package = models.ForeignKey(Package)
    enabled = models.BooleanField(default=True)
