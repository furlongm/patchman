# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    if db.backend_name == 'mysql':
        db.execute('SET storage_engine=INNODB')
    
    def forwards(self, orm):
        
        # Adding model 'PackageName'
        db.create_table('packages_packagename', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
        ))
        db.send_create_signal('packages', ['PackageName'])

        # Adding model 'Package'
        db.create_table('packages_package', (
            ('name', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.PackageName'])),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=255, null=True, blank=True)),
            ('packagetype', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
            ('epoch', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('release', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('arch', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['arch.PackageArchitecture'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('packages', ['Package'])

        # Adding model 'PackageUpdate'
        db.create_table('packages_packageupdate', (
            ('newpackage', self.gf('django.db.models.fields.related.ForeignKey')(related_name='newpackage', to=orm['packages.Package'])),
            ('security', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('oldpackage', self.gf('django.db.models.fields.related.ForeignKey')(related_name='oldpackage', to=orm['packages.Package'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('packages', ['PackageUpdate'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'PackageName'
        db.delete_table('packages_packagename')

        # Deleting model 'Package'
        db.delete_table('packages_package')

        # Deleting model 'PackageUpdate'
        db.delete_table('packages_packageupdate')
    
    
    models = {
        'arch.packagearchitecture': {
            'Meta': {'object_name': 'PackageArchitecture'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
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
            'Meta': {'object_name': 'PackageName'},
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
            'security': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        }
    }
    
    complete_apps = ['packages']
