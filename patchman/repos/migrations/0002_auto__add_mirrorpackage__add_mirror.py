# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    if db.backend_name == 'mysql':
        db.execute('SET storage_engine=INNODB')

    def forwards(self, orm):
        
        # Adding model 'MirrorPackage'
        db.create_table('repos_mirrorpackage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mirror', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['repos.Mirror'])),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.Package'])),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('repos', ['MirrorPackage'])

        # Adding model 'Mirror'
        db.create_table('repos_mirror', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('repo', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['repos.Repository'])),
            ('url', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('last_access_ok', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('file_checksum', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('repos', ['Mirror'])


    def backwards(self, orm):
        
        # Deleting model 'MirrorPackage'
        db.delete_table('repos_mirrorpackage')

        # Deleting model 'Mirror'
        db.delete_table('repos_mirror')


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
