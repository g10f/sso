# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Don't use "from appname.models import ModelName". 
        # Use orm.ModelName to refer to models in this application,
        # and orm['appname.ModelName'] for models in other applications.
        try:
            organisation_user_admin_group = orm['auth.Group'].objects.get(name='OrganisationUserAdmin')
            sso_centeradmin_role = orm.ApplicationRole.objects.get(application__uuid=settings.APP_UUID, role__name='CenterAdmin')
            
            for user in orm.User.objects.filter(is_staff=True, is_superuser=False, groups=organisation_user_admin_group):
                user.is_staff = False
                user.application_roles.add(sso_centeradmin_role)
                user.groups.remove(organisation_user_admin_group)
                user.save()
    
        except ObjectDoesNotExist:
            pass
        
        try:
            global_user_admin_group = orm['auth.Group'].objects.get(name='GlobalUserAdmin')
            sso_globaladmin_role = orm.ApplicationRole.objects.get(application__uuid=settings.APP_UUID, role__name='GlobalAdmin')
    
            for user in orm.User.objects.filter(is_staff=True, is_superuser=False, groups=global_user_admin_group):
                user.is_staff = False
                user.application_roles.add(sso_globaladmin_role)
                user.groups.remove(global_user_admin_group)
                user.save()
        except ObjectDoesNotExist:
            pass
        
    def backwards(self, orm):
        "Write your backwards methods here."
        try:
            organisation_user_admin_group = orm['auth.Group'].objects.get(name='OrganisationUserAdmin')
            sso_centeradmin_role = orm.ApplicationRole.objects.get(application__uuid=settings.APP_UUID, role__name='CenterAdmin')
    
            for user in orm.User.objects.filter(is_staff=False, is_superuser=False, application_roles=sso_centeradmin_role):
                user.is_staff = True
                user.application_roles.remove(sso_centeradmin_role)
                user.groups.add(organisation_user_admin_group)
                user.save()
        except ObjectDoesNotExist:
            pass

        try:
            global_user_admin_group = orm['auth.Group'].objects.get(name='GlobalUserAdmin')
            sso_globaladmin_role = orm.ApplicationRole.objects.get(application__uuid=settings.APP_UUID, role__name='GlobalAdmin')
            
            for user in orm.User.objects.filter(is_staff=False, is_superuser=False, application_roles=sso_globaladmin_role):
                user.is_staff = True
                user.application_roles.remove(sso_globaladmin_role)
                user.groups.add(global_user_admin_group)
                user.save()
        except ObjectDoesNotExist:
            pass

    models = {
        u'accounts.application': {
            'Meta': {'ordering': "['order', 'title']", 'object_name': 'Application'},
            'enable_url': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '2047', 'blank': 'True'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'accounts.applicationrole': {
            'Meta': {'ordering': "['application', 'role']", 'unique_together': "(('application', 'role'),)", 'object_name': 'ApplicationRole'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['accounts.Application']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_inheritable_by_global_admin': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_inheritable_by_org_admin': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'role': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['accounts.Role']"})
        },
        u'accounts.organisation': {
            'Meta': {'ordering': "['name']", 'object_name': 'Organisation'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'iso2_code': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['accounts.Region']", 'null': 'True', 'blank': 'True'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'accounts.region': {
            'Meta': {'ordering': "['name']", 'object_name': 'Region'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'accounts.role': {
            'Meta': {'ordering': "['order', 'name']", 'object_name': 'Role'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'accounts.user': {
            'Meta': {'object_name': 'User'},
            'application_roles': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['accounts.ApplicationRole']", 'null': 'True', 'blank': 'True'}),
            'created_by_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['accounts.User']"}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_center': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_subscriber': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'last_modified_by_user': ('current_user.models.CurrentUserField', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['accounts.User']"}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'organisations': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['accounts.Organisation']", 'null': 'True', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'picture': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
        },
        u'accounts.userassociatedsystem': {
            'Meta': {'unique_together': "(('application', 'userid'),)", 'object_name': 'UserAssociatedSystem'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['accounts.Application']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['accounts.User']"}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['accounts']
    symmetrical = True
