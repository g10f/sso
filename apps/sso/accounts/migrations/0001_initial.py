# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Application'
        db.create_table(u'accounts_application', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=2047, blank=True)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('global_navigation', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'accounts', ['Application'])

        # Adding model 'Role'
        db.create_table(u'accounts_role', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('order', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.Group'], null=True, blank=True)),
        ))
        db.send_create_signal(u'accounts', ['Role'])

        # Adding model 'ApplicationRole'
        db.create_table(u'accounts_applicationrole', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('application', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounts.Application'])),
            ('role', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounts.Role'])),
            ('is_inheritable_by_org_admin', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('is_inheritable_by_global_admin', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'accounts', ['ApplicationRole'])

        # Adding unique constraint on 'ApplicationRole', fields ['application', 'role']
        db.create_unique(u'accounts_applicationrole', ['application_id', 'role_id'])

        # Adding model 'RoleProfile'
        db.create_table(u'accounts_roleprofile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('order', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('is_inheritable_by_org_admin', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('is_inheritable_by_global_admin', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'accounts', ['RoleProfile'])

        # Adding M2M table for field application_roles on 'RoleProfile'
        m2m_table_name = db.shorten_name(u'accounts_roleprofile_application_roles')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('roleprofile', models.ForeignKey(orm[u'accounts.roleprofile'], null=False)),
            ('applicationrole', models.ForeignKey(orm[u'accounts.applicationrole'], null=False))
        ))
        db.create_unique(m2m_table_name, ['roleprofile_id', 'applicationrole_id'])

        # Adding model 'Region'
        db.create_table(u'accounts_region', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'accounts', ['Region'])

        # Adding model 'Organisation'
        db.create_table(u'accounts_organisation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('iso2_code', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('last_update', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('region', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounts.Region'], null=True, blank=True)),
        ))
        db.send_create_signal(u'accounts', ['Organisation'])

        # Adding model 'User'
        db.create_table(u'accounts_user', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('last_login', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('is_superuser', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('username', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('is_staff', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('date_joined', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('uuid', self.gf('sso.fields.UUIDField')(version=4, max_length=36, blank=True, unique=True, name='uuid')),
            ('last_modified_by_user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['accounts.User'])),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('created_by_user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['accounts.User'])),
            ('is_center', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_subscriber', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('picture', self.gf(u'sorl.thumbnail.fields.ImageField')(max_length=100, blank=True)),
            ('notes', self.gf('django.db.models.fields.TextField')(max_length=1024, blank=True)),
        ))
        db.send_create_signal(u'accounts', ['User'])

        # Adding M2M table for field groups on 'User'
        m2m_table_name = db.shorten_name(u'accounts_user_groups')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'accounts.user'], null=False)),
            ('group', models.ForeignKey(orm[u'auth.group'], null=False))
        ))
        db.create_unique(m2m_table_name, ['user_id', 'group_id'])

        # Adding M2M table for field user_permissions on 'User'
        m2m_table_name = db.shorten_name(u'accounts_user_user_permissions')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'accounts.user'], null=False)),
            ('permission', models.ForeignKey(orm[u'auth.permission'], null=False))
        ))
        db.create_unique(m2m_table_name, ['user_id', 'permission_id'])

        # Adding M2M table for field organisations on 'User'
        m2m_table_name = db.shorten_name(u'accounts_user_organisations')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'accounts.user'], null=False)),
            ('organisation', models.ForeignKey(orm[u'accounts.organisation'], null=False))
        ))
        db.create_unique(m2m_table_name, ['user_id', 'organisation_id'])

        # Adding M2M table for field application_roles on 'User'
        m2m_table_name = db.shorten_name(u'accounts_user_application_roles')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'accounts.user'], null=False)),
            ('applicationrole', models.ForeignKey(orm[u'accounts.applicationrole'], null=False))
        ))
        db.create_unique(m2m_table_name, ['user_id', 'applicationrole_id'])

        # Adding M2M table for field role_profiles on 'User'
        m2m_table_name = db.shorten_name(u'accounts_user_role_profiles')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'accounts.user'], null=False)),
            ('roleprofile', models.ForeignKey(orm[u'accounts.roleprofile'], null=False))
        ))
        db.create_unique(m2m_table_name, ['user_id', 'roleprofile_id'])

        # Adding model 'UserAssociatedSystem'
        db.create_table(u'accounts_userassociatedsystem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounts.User'])),
            ('application', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounts.Application'])),
            ('userid', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'accounts', ['UserAssociatedSystem'])

        # Adding unique constraint on 'UserAssociatedSystem', fields ['application', 'userid']
        db.create_unique(u'accounts_userassociatedsystem', ['application_id', 'userid'])


    def backwards(self, orm):
        # Removing unique constraint on 'UserAssociatedSystem', fields ['application', 'userid']
        db.delete_unique(u'accounts_userassociatedsystem', ['application_id', 'userid'])

        # Removing unique constraint on 'ApplicationRole', fields ['application', 'role']
        db.delete_unique(u'accounts_applicationrole', ['application_id', 'role_id'])

        # Deleting model 'Application'
        db.delete_table(u'accounts_application')

        # Deleting model 'Role'
        db.delete_table(u'accounts_role')

        # Deleting model 'ApplicationRole'
        db.delete_table(u'accounts_applicationrole')

        # Deleting model 'RoleProfile'
        db.delete_table(u'accounts_roleprofile')

        # Removing M2M table for field application_roles on 'RoleProfile'
        db.delete_table(db.shorten_name(u'accounts_roleprofile_application_roles'))

        # Deleting model 'Region'
        db.delete_table(u'accounts_region')

        # Deleting model 'Organisation'
        db.delete_table(u'accounts_organisation')

        # Deleting model 'User'
        db.delete_table(u'accounts_user')

        # Removing M2M table for field groups on 'User'
        db.delete_table(db.shorten_name(u'accounts_user_groups'))

        # Removing M2M table for field user_permissions on 'User'
        db.delete_table(db.shorten_name(u'accounts_user_user_permissions'))

        # Removing M2M table for field organisations on 'User'
        db.delete_table(db.shorten_name(u'accounts_user_organisations'))

        # Removing M2M table for field application_roles on 'User'
        db.delete_table(db.shorten_name(u'accounts_user_application_roles'))

        # Removing M2M table for field role_profiles on 'User'
        db.delete_table(db.shorten_name(u'accounts_user_role_profiles'))

        # Deleting model 'UserAssociatedSystem'
        db.delete_table(u'accounts_userassociatedsystem')


    models = {
        u'accounts.application': {
            'Meta': {'ordering': "['order', 'title']", 'object_name': 'Application'},
            'global_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
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
        u'accounts.roleprofile': {
            'Meta': {'ordering': "['order', 'name']", 'object_name': 'RoleProfile'},
            'application_roles': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['accounts.ApplicationRole']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_inheritable_by_global_admin': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_inheritable_by_org_admin': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'uuid': ('sso.fields.UUIDField', [], {'version': '4', 'max_length': '36', 'blank': 'True', 'unique': 'True', 'name': "'uuid'"})
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
            'notes': ('django.db.models.fields.TextField', [], {'max_length': '1024', 'blank': 'True'}),
            'organisations': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['accounts.Organisation']", 'null': 'True', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'picture': (u'sorl.thumbnail.fields.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'role_profiles': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['accounts.RoleProfile']", 'null': 'True', 'blank': 'True'}),
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