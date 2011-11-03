# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding unique constraint on 'Package', fields ['name', 'packagetype', 'epoch', 'version', 'release', 'arch']
        db.create_unique('packages_package', ['name_id', 'packagetype', 'epoch', 'version', 'release', 'arch_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Package', fields ['name', 'packagetype', 'epoch', 'version', 'release', 'arch']
        db.delete_unique('packages_package', ['name_id', 'packagetype', 'epoch', 'version', 'release', 'arch_id'])


    models = {
        'arch.packagearchitecture': {
            'Meta': {'object_name': 'PackageArchitecture'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
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
        'packages.packagestring': {
            'Meta': {'object_name': 'PackageString', 'managed': 'False'},
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'epoch': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'packagetype': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'release': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'packages.packageupdate': {
            'Meta': {'object_name': 'PackageUpdate'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'newpackage': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newpackage'", 'to': "orm['packages.Package']"}),
            'oldpackage': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'oldpackage'", 'to': "orm['packages.Package']"}),
            'security': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['packages']
