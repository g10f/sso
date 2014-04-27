# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'AdminRegion'
        db.create_table(u'organisations_adminregion', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'organisations', ['AdminRegion'])

        # Adding model 'Organisation'
        db.create_table(u'organisations_organisation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['l10n.Country'], null=True, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('homepage', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('notes', self.gf('django.db.models.fields.TextField')(max_length=255, blank=True)),
            ('center_type', self.gf('django.db.models.fields.CharField')(max_length=2, db_index=True)),
            ('centerid', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('founded', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('latitude', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=9, decimal_places=6, blank=True)),
            ('longitude', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=9, decimal_places=6, blank=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('is_private', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('admin_region', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['organisations.AdminRegion'], null=True, blank=True)),
        ))
        db.send_create_signal(u'organisations', ['Organisation'])

        # Adding model 'OrganisationAddress'
        db.create_table(u'organisations_organisationaddress', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True)),
            ('addressee', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('street_address', self.gf('django.db.models.fields.TextField')(max_length=512, blank=True)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('postal_code', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['l10n.Country'])),
            ('state', self.gf('smart_selects.db_fields.ChainedForeignKey')(to=orm['l10n.AdminArea'], null=True, blank=True)),
            ('primary', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('address_type', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('organisation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['organisations.Organisation'])),
            ('careof', self.gf('django.db.models.fields.CharField')(default='', max_length=80, blank=True)),
        ))
        db.send_create_signal(u'organisations', ['OrganisationAddress'])

        # Adding unique constraint on 'OrganisationAddress', fields ['organisation', 'address_type']
        db.create_unique(u'organisations_organisationaddress', ['organisation_id', 'address_type'])

        # Adding model 'OrganisationPhoneNumber'
        db.create_table(u'organisations_organisationphonenumber', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('primary', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('phone_type', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('organisation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['organisations.Organisation'])),
        ))
        db.send_create_signal(u'organisations', ['OrganisationPhoneNumber'])


    def backwards(self, orm):
        # Removing unique constraint on 'OrganisationAddress', fields ['organisation', 'address_type']
        db.delete_unique(u'organisations_organisationaddress', ['organisation_id', 'address_type'])

        # Deleting model 'AdminRegion'
        db.delete_table(u'organisations_adminregion')

        # Deleting model 'Organisation'
        db.delete_table(u'organisations_organisation')

        # Deleting model 'OrganisationAddress'
        db.delete_table(u'organisations_organisationaddress')

        # Deleting model 'OrganisationPhoneNumber'
        db.delete_table(u'organisations_organisationphonenumber')


    models = {
        u'l10n.adminarea': {
            'Meta': {'ordering': "('name',)", 'object_name': 'AdminArea'},
            'abbrev': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['l10n.Country']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'})
        },
        u'l10n.country': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Country'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'admin_area': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'continent': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'iso2_code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '2'}),
            'iso3_code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'numcode': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'printable_name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'organisations.adminregion': {
            'Meta': {'ordering': "['name']", 'object_name': 'AdminRegion'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'organisations.organisation': {
            'Meta': {'ordering': "['name']", 'object_name': 'Organisation'},
            'admin_region': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['organisations.AdminRegion']", 'null': 'True', 'blank': 'True'}),
            'center_type': ('django.db.models.fields.CharField', [], {'max_length': '2', 'db_index': 'True'}),
            'centerid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['l10n.Country']", 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'founded': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'latitude': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '9', 'decimal_places': '6', 'blank': 'True'}),
            'longitude': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '9', 'decimal_places': '6', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'max_length': '255', 'blank': 'True'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'organisations.organisationaddress': {
            'Meta': {'ordering': "['addressee']", 'unique_together': "(('organisation', 'address_type'),)", 'object_name': 'OrganisationAddress'},
            'address_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'addressee': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'careof': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '80', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['l10n.Country']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'organisation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['organisations.Organisation']"}),
            'postal_code': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('smart_selects.db_fields.ChainedForeignKey', [], {'to': u"orm['l10n.AdminArea']", 'null': 'True', 'blank': 'True'}),
            'street_address': ('django.db.models.fields.TextField', [], {'max_length': '512', 'blank': 'True'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'organisations.organisationphonenumber': {
            'Meta': {'ordering': "['-primary']", 'object_name': 'OrganisationPhoneNumber'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'organisation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['organisations.Organisation']"}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'phone_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        }
    }

    complete_apps = ['organisations']