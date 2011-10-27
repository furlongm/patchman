# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        for r in orm.Repository.objects.all():
            mirror = orm.Mirror.objects.create(
                repo = r,
                url = r.url,
                last_access_ok = r.last_access_ok,
                file_checksum = r.file_checksum,
                timestamp = r.timestamp,
            )
            for p in r.packages.all():
                orm.MirrorPackage.objects.create(
                    mirror = mirror,
                    package = p.package,
                    enabled = p.enabled
                )
            


    def backwards(self, orm):
        "Write your backwards methods here."


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
        'packages.package': {
            'Meta': {'ordering': "('name', 'epoch', 'version', 'release', 'arch')", 'object_name': 'Package'},
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
        'repos.mirror': {
            'Meta': {'object_name': 'Mirror'},
            'file_checksum': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_access_ok': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['packages.Package']", 'null': 'True', 'through': "orm['repos.MirrorPackage']", 'blank': 'True'}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['repos.Repository']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'repos.mirrorpackage': {
            'Meta': {'object_name': 'MirrorPackage'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mirror': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['repos.Mirror']"}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"})
        },
        'repos.repopackage': {
            'Meta': {'object_name': 'RepoPackage'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['repos.Repository']"})
        },
        'repos.repository': {
            'Meta': {'object_name': 'Repository'},
            'arch': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['arch.MachineArchitecture']"}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'file_checksum': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_access_ok': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['packages.Package']", 'null': 'True', 'through': "orm['repos.RepoPackage']", 'blank': 'True'}),
            'repotype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'security': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['repos']
