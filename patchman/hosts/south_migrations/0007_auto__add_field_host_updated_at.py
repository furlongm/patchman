# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):


    if db.backend_name == 'mysql':
        db.execute('SET storage_engine=INNODB')

    def forwards(self, orm):
        # Adding field 'Host.updated_at'
        db.add_column(u'hosts_host', 'updated_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2014, 1, 23, 0, 0)),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Host.updated_at'
        db.delete_column(u'hosts_host', 'updated_at')


    models = {
        u'arch.machinearchitecture': {
            'Meta': {'object_name': 'MachineArchitecture'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        u'arch.packagearchitecture': {
            'Meta': {'object_name': 'PackageArchitecture'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        u'domains.domain': {
            'Meta': {'object_name': 'Domain'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        u'hosts.host': {
            'Meta': {'ordering': "('hostname',)", 'object_name': 'Host'},
            'arch': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['arch.MachineArchitecture']"}),
            'check_dns': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'domain': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['domains.Domain']"}),
            'host_repos_only': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipaddress': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'lastreport': ('django.db.models.fields.DateTimeField', [], {}),
            'os': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['operatingsystems.OS']"}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['packages.Package']", 'symmetrical': 'False'}),
            'reboot_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'repos': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['repos.Repository']", 'through': u"orm['hosts.HostRepo']", 'symmetrical': 'False'}),
            'reversedns': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2014, 1, 23, 0, 0)'}),
            'updates': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['packages.PackageUpdate']", 'symmetrical': 'False'})
        },
        u'hosts.hostrepo': {
            'Meta': {'unique_together': "(('host', 'repo'),)", 'object_name': 'HostRepo'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['hosts.Host']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['repos.Repository']"})
        },
        u'operatingsystems.os': {
            'Meta': {'object_name': 'OS'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'osgroup': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['operatingsystems.OSGroup']", 'null': 'True', 'blank': 'True'})
        },
        u'operatingsystems.osgroup': {
            'Meta': {'object_name': 'OSGroup'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'repos': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['repos.Repository']", 'null': 'True', 'blank': 'True'})
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
        u'packages.packageupdate': {
            'Meta': {'object_name': 'PackageUpdate'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'newpackage': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newpackage'", 'to': u"orm['packages.Package']"}),
            'oldpackage': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'oldpackage'", 'to': u"orm['packages.Package']"}),
            'security': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'repos.repository': {
            'Meta': {'object_name': 'Repository'},
            'arch': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['arch.MachineArchitecture']"}),
            'auth_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'repo_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'repotype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'security': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['hosts']
