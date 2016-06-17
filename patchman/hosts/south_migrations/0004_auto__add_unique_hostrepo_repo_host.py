# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    if db.backend_name == 'mysql':
        db.execute('SET storage_engine=INNODB')

    def forwards(self, orm):

        if not db.dry_run:
            # Remove existing duplicates
            hostrepos = []
            for hostrepo in orm.HostRepo.objects.all():
                hr_string = '{0!s}-{1!s}'.format(hostrepo.host.id, hostrepo.repo.id)
                if hr_string in hostrepos:
                    hostrepo.delete()
                else:
                    hostrepos.append(hr_string)

        # Adding unique constraint on 'HostRepo', fields ['repo', 'host']
        db.create_unique('hosts_hostrepo', ['repo_id', 'host_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'HostRepo', fields ['repo', 'host']
        db.delete_unique('hosts_hostrepo', ['repo_id', 'host_id'])


    models = {
        'arch.machinearchitecture': {
            'Meta': {'object_name': 'MachineArchitecture'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'arch.packagearchitecture': {
            'Meta': {'object_name': 'PackageArchitecture'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'domains.domain': {
            'Meta': {'object_name': 'Domain'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'hosts.host': {
            'Meta': {'ordering': "('hostname',)", 'object_name': 'Host'},
            'arch': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['arch.MachineArchitecture']"}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['domains.Domain']"}),
            'host_repos_only': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hostname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipaddress': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'lastreport': ('django.db.models.fields.DateTimeField', [], {}),
            'os': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['operatingsystems.OS']"}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.Package']", 'symmetrical': 'False'}),
            'reboot_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'repos': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['repos.Repository']", 'through': "orm['hosts.HostRepo']", 'symmetrical': 'False'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'updates': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.PackageUpdate']", 'symmetrical': 'False'})
        },
        'hosts.hostrepo': {
            'Meta': {'unique_together': "(('host', 'repo'),)", 'object_name': 'HostRepo'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['hosts.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['repos.Repository']"})
        },
        'operatingsystems.os': {
            'Meta': {'object_name': 'OS'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'osgroup': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['operatingsystems.OSGroup']", 'null': 'True', 'blank': 'True'})
        },
        'operatingsystems.osgroup': {
            'Meta': {'object_name': 'OSGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'repos': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['repos.Repository']", 'null': 'True', 'blank': 'True'})
        },
        'packages.package': {
            'Meta': {'ordering': "('name', 'epoch', 'version', 'release', 'arch')", 'unique_together': "(('name', 'epoch', 'version', 'release', 'arch', 'packagetype'),)", 'object_name': 'Package'},
            'arch': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['arch.PackageArchitecture']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'epoch': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.PackageName']"}),
            'packagetype': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'release': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'packages.packagename': {
            'Meta': {'ordering': "('name',)", 'object_name': 'PackageName'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'packages.packageupdate': {
            'Meta': {'object_name': 'PackageUpdate'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'newpackage': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newpackage'", 'to': "orm['packages.Package']"}),
            'oldpackage': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'oldpackage'", 'to': "orm['packages.Package']"}),
            'security': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'repos.repository': {
            'Meta': {'object_name': 'Repository'},
            'arch': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['arch.MachineArchitecture']"}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'repotype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'security': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['hosts']
