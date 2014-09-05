# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'OrganisationCountry.email'
        db.alter_column(u'organisations_organisationcountry', 'email_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['emails.Email'], null=True, on_delete=models.SET_NULL))

        # Changing field 'AdminRegion.email'
        db.alter_column(u'organisations_adminregion', 'email_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['emails.Email'], unique=True, null=True, on_delete=models.SET_NULL))
        # Adding field 'Organisation.coordinates_type'
        db.add_column(u'organisations_organisation', 'coordinates_type',
                      self.gf('django.db.models.fields.CharField')(default='3', max_length=1, db_index=True),
                      keep_default=False)


        # Changing field 'Organisation.email'
        db.alter_column(u'organisations_organisation', 'email_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['emails.Email'], null=True, on_delete=models.SET_NULL))

    def backwards(self, orm):

        # Changing field 'OrganisationCountry.email'
        db.alter_column(u'organisations_organisationcountry', 'email_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['emails.Email'], null=True))

        # Changing field 'AdminRegion.email'
        db.alter_column(u'organisations_adminregion', 'email_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['emails.Email'], unique=True, null=True))
        # Deleting field 'Organisation.coordinates_type'
        db.delete_column(u'organisations_organisation', 'coordinates_type')


        # Changing field 'Organisation.email'
        db.alter_column(u'organisations_organisation', 'email_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['emails.Email'], null=True))

    models = {
        u'emails.email': {
            'Meta': {'ordering': "['email']", 'object_name': 'Email'},
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            'email_type': ('django.db.models.fields.CharField', [], {'max_length': '20', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'permission': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '20', 'db_index': 'True'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
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
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['l10n.Country']"}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['emails.Email']", 'unique': 'True', 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'organisations.countrygroup': {
            'Meta': {'ordering': "['name']", 'object_name': 'CountryGroup'},
            'email': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['emails.Email']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'organisations.organisation': {
            'Meta': {'ordering': "['name']", 'object_name': 'Organisation'},
            'admin_region': ('smart_selects.db_fields.ChainedForeignKey', [], {'to': u"orm['organisations.AdminRegion']", 'null': 'True', 'blank': 'True'}),
            'can_publish': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'center_type': ('django.db.models.fields.CharField', [], {'max_length': '2', 'db_index': 'True'}),
            'centerid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'coordinates_type': ('django.db.models.fields.CharField', [], {'default': "'3'", 'max_length': '1', 'db_index': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['l10n.Country']", 'null': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['emails.Email']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'founded': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'latitude': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '9', 'decimal_places': '6', 'blank': 'True'}),
            'longitude': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '9', 'decimal_places': '6', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
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
            'region': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'state': ('smart_selects.db_fields.ChainedForeignKey', [], {'to': u"orm['l10n.AdminArea']", 'null': 'True', 'blank': 'True'}),
            'street_address': ('django.db.models.fields.TextField', [], {'max_length': '512', 'blank': 'True'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'organisations.organisationcountry': {
            'Meta': {'ordering': "['country']", 'object_name': 'OrganisationCountry'},
            'country': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['l10n.Country']", 'unique': 'True', 'null': 'True'}),
            'country_groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['organisations.CountryGroup']", 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['emails.Email']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
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