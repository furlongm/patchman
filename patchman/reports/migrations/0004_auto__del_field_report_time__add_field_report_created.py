# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):


    if db.backend_name == 'mysql':
        db.execute('SET storage_engine=INNODB')


    def forwards(self, orm):
        # Renaming field 'Report.time' to 'Report.created'
        db.rename_column(u'reports_report', 'time', 'created')


    def backwards(self, orm):

        # Renaming field 'Report.created' to 'Report.time'
        db.rename_column(u'reports_report', 'created', 'time')


    models = {
        u'reports.report': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Report'},
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'bug_updates': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'packages': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'protocol': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'reboot': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'report_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True'}),
            'repos': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'sec_updates': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True'}),
            'useragent': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'})
        }
    }

    complete_apps = ['reports']
