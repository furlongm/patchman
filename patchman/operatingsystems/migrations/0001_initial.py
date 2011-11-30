# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    if db.backend_name == 'mysql':
        db.execute('SET storage_engine=INNODB')
    
    def forwards(self, orm):
        
        # Adding model 'OSGroup'
        db.create_table('operatingsystems_osgroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
        ))
        db.send_create_signal('operatingsystems', ['OSGroup'])

        # Adding M2M table for field repos on 'OSGroup'
        db.create_table('operatingsystems_osgroup_repos', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('osgroup', models.ForeignKey(orm['operatingsystems.osgroup'], null=False)),
            ('repository', models.ForeignKey(orm['repos.repository'], null=False))
        ))
        db.create_unique('operatingsystems_osgroup_repos', ['osgroup_id', 'repository_id'])

        # Adding model 'OS'
        db.create_table('operatingsystems_os', (
            ('osgroup', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['operatingsystems.OSGroup'], null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
        ))
        db.send_create_signal('operatingsystems', ['OS'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'OSGroup'
        db.delete_table('operatingsystems_osgroup')

        # Removing M2M table for field repos on 'OSGroup'
        db.delete_table('operatingsystems_osgroup_repos')

        # Deleting model 'OS'
        db.delete_table('operatingsystems_os')
    
    
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
        'repos.repopackage': {
            'Meta': {'object_name': 'RepoPackage'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['repos.Repository']"})
        },
        'repos.repository': {
            'Meta': {'object_name': 'Repository'},
            'arch': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['arch.MachineArchitecture']"}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'file_checksum': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_access_ok': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['packages.Package']", 'null': 'True', 'through': "orm['repos.RepoPackage']", 'blank': 'True'}),
            'repotype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'security': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        }
    }
    
    complete_apps = ['operatingsystems']
