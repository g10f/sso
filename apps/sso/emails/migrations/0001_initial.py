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
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('email_type', self.gf('django.db.models.fields.CharField')(max_length=2, db_index=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=75)),
        ))
        db.send_create_signal(u'emails', ['Email'])

        # Adding model 'EmailForward'
        db.create_table(u'emails_emailforward', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True)),
            ('email_list', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['emails.Email'])),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
        ))
        db.send_create_signal(u'emails', ['EmailForward'])

        # Adding unique constraint on 'EmailForward', fields ['email', 'email_list']
        db.create_unique(u'emails_emailforward', ['email', 'email_list_id'])

        # Adding model 'EmailAlias'
        db.create_table(u'emails_emailalias', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True)),
            ('email_list', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['emails.Email'])),
            ('email', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=75)),
        ))
        db.send_create_signal(u'emails', ['EmailAlias'])

        # Adding unique constraint on 'EmailAlias', fields ['email', 'email_list']
        db.create_unique(u'emails_emailalias', ['email', 'email_list_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'EmailAlias', fields ['email', 'email_list']
        db.delete_unique(u'emails_emailalias', ['email', 'email_list_id'])

        # Removing unique constraint on 'EmailForward', fields ['email', 'email_list']
        db.delete_unique(u'emails_emailforward', ['email', 'email_list_id'])

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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'emails.emailalias': {
            'Meta': {'ordering': "['email', 'email_list']", 'unique_together': "(('email', 'email_list'),)", 'object_name': 'EmailAlias'},
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75'}),
            'email_list': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['emails.Email']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'emails.emailforward': {
            'Meta': {'ordering': "['email', 'email_list']", 'unique_together': "(('email', 'email_list'),)", 'object_name': 'EmailForward'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'email_list': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['emails.Email']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        }
    }

    complete_apps = ['emails']