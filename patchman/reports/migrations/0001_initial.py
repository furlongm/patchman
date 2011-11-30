# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    if db.backend_name == 'mysql':
        db.execute('SET storage_engine=INNODB')
    
    def forwards(self, orm):
        
        # Adding model 'Report'
        db.create_table('reports_report', (
            ('kernel', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('domain', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('protocol', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('tags', self.gf('django.db.models.fields.CharField')(default='', max_length=255, null=True)),
            ('os', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('repos', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('report_ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15, null=True)),
            ('host', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('processed', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('useragent', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('packages', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('arch', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('reports', ['Report'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'Report'
        db.delete_table('reports_report')
    
    
    models = {
        'reports.report': {
            'Meta': {'object_name': 'Report'},
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'packages': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'processed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'protocol': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'report_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True'}),
            'repos': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'useragent': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'})
        }
    }
    
    complete_apps = ['reports']
