# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Report.reboot'
        db.add_column('reports_report', 'reboot', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Report.reboot'
        db.delete_column('reports_report', 'reboot')


    models = {
        'reports.report': {
            'Meta': {'ordering': "('-time',)", 'object_name': 'Report'},
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'packages': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'protocol': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'reboot': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'report_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True'}),
            'repos': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'useragent': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'})
        }
    }

    complete_apps = ['reports']
