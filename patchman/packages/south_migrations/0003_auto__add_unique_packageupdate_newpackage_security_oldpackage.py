# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    if db.backend_name == 'mysql':
        db.execute('SET storage_engine=INNODB')

    def forwards(self, orm):
        # Adding unique constraint on 'PackageUpdate', fields ['newpackage', 'security', 'oldpackage']
        db.create_unique(u'packages_packageupdate', ['newpackage_id', 'security', 'oldpackage_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'PackageUpdate', fields ['newpackage', 'security', 'oldpackage']
        db.delete_unique(u'packages_packageupdate', ['newpackage_id', 'security', 'oldpackage_id'])


    models = {
        u'arch.packagearchitecture': {
            'Meta': {'object_name': 'PackageArchitecture'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        u'packages.package': {
            'Meta': {'ordering': "('name', 'epoch', 'version', 'release', 'arch')", 'unique_together': "(('name', 'epoch', 'version', 'release', 'arch', 'packagetype'),)", 'object_name': 'Package'},
            'arch': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['arch.PackageArchitecture']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'epoch': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['packages.PackageName']"}),
            'packagetype': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'release': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'packages.packagename': {
            'Meta': {'ordering': "('name',)", 'object_name': 'PackageName'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        u'packages.packagestring': {
            'Meta': {'object_name': 'PackageString', 'managed': 'False'},
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'epoch': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'packagetype': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'release': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'packages.packageupdate': {
            'Meta': {'unique_together': "(('oldpackage', 'newpackage', 'security'),)", 'object_name': 'PackageUpdate'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'newpackage': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newpackage'", 'to': u"orm['packages.Package']"}),
            'oldpackage': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'oldpackage'", 'to': u"orm['packages.Package']"}),
            'security': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['packages']
