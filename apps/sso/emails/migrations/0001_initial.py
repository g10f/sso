# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Email'
        db.create_table(u'emails_email', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('email_type', self.gf('django.db.models.fields.CharField')(max_length=2, db_index=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=75)),
        ))
        db.send_create_signal(u'emails', ['Email'])

        # Adding model 'EmailForward'
        db.create_table(u'emails_emailforward', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True)),
            ('email', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['emails.Email'])),
            ('forward', self.gf('django.db.models.fields.EmailField')(max_length=75)),
        ))
        db.send_create_signal(u'emails', ['EmailForward'])

        # Adding unique constraint on 'EmailForward', fields ['email', 'forward']
        db.create_unique(u'emails_emailforward', ['email_id', 'forward'])

        # Adding model 'EmailAlias'
        db.create_table(u'emails_emailalias', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True)),
            ('email', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['emails.Email'])),
            ('alias', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=75)),
        ))
        db.send_create_signal(u'emails', ['EmailAlias'])

        # Adding unique constraint on 'EmailAlias', fields ['email', 'alias']
        db.create_unique(u'emails_emailalias', ['email_id', 'alias'])


    def backwards(self, orm):
        # Removing unique constraint on 'EmailAlias', fields ['email', 'alias']
        db.delete_unique(u'emails_emailalias', ['email_id', 'alias'])

        # Removing unique constraint on 'EmailForward', fields ['email', 'forward']
        db.delete_unique(u'emails_emailforward', ['email_id', 'forward'])

        # Deleting model 'Email'
        db.delete_table(u'emails_email')

        # Deleting model 'EmailForward'
        db.delete_table(u'emails_emailforward')

        # Deleting model 'EmailAlias'
        db.delete_table(u'emails_emailalias')


    models = {
        u'emails.email': {
            'Meta': {'ordering': "['email']", 'object_name': 'Email'},
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75'}),
            'email_type': ('django.db.models.fields.CharField', [], {'max_length': '2', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'emails.emailalias': {
            'Meta': {'ordering': "['alias', 'email']", 'unique_together': "(('email', 'alias'),)", 'object_name': 'EmailAlias'},
            'alias': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['emails.Email']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'emails.emailforward': {
            'Meta': {'ordering': "['forward', 'email']", 'unique_together': "(('email', 'forward'),)", 'object_name': 'EmailForward'},
            'email': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['emails.Email']"}),
            'forward': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        }
    }

    complete_apps = ['emails']