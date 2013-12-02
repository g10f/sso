# -*- coding: utf-8 -*-
from django.db import models
from django.utils.crypto import constant_time_compare
from django.conf import settings
 
class StreamingUser(models.Model):
    id_nr = models.IntegerField(primary_key=True)
    email = models.CharField(max_length=300)
    password = models.CharField(max_length=90)
    center = models.CharField(max_length=3)
    admin = models.CharField(max_length=3)
    ip = models.CharField(max_length=45, blank=True)
    registrar = models.ForeignKey('self', db_column='registrar', null=True)
    mailsent = models.CharField(max_length=3)
    created = models.DateTimeField()
    subscriber = models.CharField(max_length=3)
    
    def check_password(self, raw_password):
        encoded_2 = raw_password.encode('base64')
        encoded = self.password + '\n'
        return constant_time_compare(encoded, encoded_2)
    
    class Meta:
        db_table = u'streaming_user'
        if not settings.TEST:
            managed = False
    
    def __unicode__(self):
        return u"%s" % (self.email)


class Logging(models.Model):
    id = models.BigIntegerField(primary_key=True, db_column='ID')  # Field name made lowercase.
    user = models.ForeignKey(StreamingUser, db_column='userid')
    action = models.CharField(max_length=45)
    date = models.DateTimeField()
    ip = models.CharField(max_length=45)
    
    class Meta:
        db_table = u'logging'
        if not settings.TEST:
            managed = False
