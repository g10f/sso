# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Email.email'
        db.alter_column(u'emails_email', 'email', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=254))

        # Changing field 'EmailAlias.alias'
        db.alter_column(u'emails_emailalias', 'alias', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=254))
        # Adding field 'EmailForward.primary'
        db.add_column(u'emails_emailforward', 'primary',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


        # Changing field 'EmailForward.forward'
        db.alter_column(u'emails_emailforward', 'forward', self.gf('django.db.models.fields.EmailField')(max_length=254))

    def backwards(self, orm):

        # Changing field 'Email.email'
        db.alter_column(u'emails_email', 'email', self.gf('django.db.models.fields.EmailField')(max_length=75, unique=True))

        # Changing field 'EmailAlias.alias'
        db.alter_column(u'emails_emailalias', 'alias', self.gf('django.db.models.fields.EmailField')(max_length=75, unique=True))
        # Deleting field 'EmailForward.primary'
        db.delete_column(u'emails_emailforward', 'primary')


        # Changing field 'EmailForward.forward'
        db.alter_column(u'emails_emailforward', 'forward', self.gf('django.db.models.fields.EmailField')(max_length=75))

    models = {
        u'emails.email': {
            'Meta': {'ordering': "['email']", 'object_name': 'Email'},
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            'email_type': ('django.db.models.fields.CharField', [], {'max_length': '2', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'emails.emailalias': {
            'Meta': {'ordering': "['alias', 'email']", 'unique_together': "(('email', 'alias'),)", 'object_name': 'EmailAlias'},
            'alias': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['emails.Email']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'emails.emailforward': {
            'Meta': {'ordering': "['forward', 'email']", 'unique_together': "(('email', 'forward'),)", 'object_name': 'EmailForward'},
            'email': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['emails.Email']"}),
            'forward': ('django.db.models.fields.EmailField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        }
    }

    complete_apps = ['emails']