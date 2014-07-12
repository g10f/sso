# -*- coding: utf-8 -*-
from django.contrib import messages
from django.utils.encoding import force_text
from django.views import generic
from django.contrib.staticfiles.templatetags.staticfiles import static
from django import forms
from django.utils.translation import ugettext_lazy as _

from sso.views import main
from sso.forms.helpers import ErrorList

import logging
logger = logging.getLogger(__name__)


class ListView(generic.ListView):
    paginate_by = 20
    page_kwarg = main.PAGE_VAR

    def get_paginate_by(self, queryset):
        try:
            return int(self.request.GET.get(main.PAGE_SIZE_VAR, self.paginate_by))
        except ValueError:
            return self.paginate_by
    

class FormsetsUpdateView(generic.UpdateView):
    
    def get_formsets(self):
        """
        returns an array of formsets (use django inlineformset_factory)
        override in subclass
        """
        raise NotImplementedError
        
    @property
    def media(self):
        js = ['formsets.js']
        return forms.Media(js=[static('js/%s' % url) for url in js]) 

    @property
    def formsets(self):
        if not hasattr(self, '_formsets'):
            self._formsets = self.get_formsets()
        return self._formsets
    
    @property
    def is_valid(self):
        form_class = self.get_form_class()
        form = self.get_form(form_class)        

        if not form.is_valid():
            return False
        
        for formset in self.formsets:
            if not formset.is_valid():
                return False
        return True
    
    def get_context_data(self, **kwargs):
        form = kwargs.get("form")
        
        media = self.media + form.media
        formsets = self.formsets
        for fs in formsets:
            media = media + fs.media
        
        errors = ErrorList(form, formsets)
        active = ''
        if errors:
            if not form.is_valid():
                active = 'object'
            else:  # set the first formset with an error as active
                for formset in formsets:
                    if not formset.is_valid():
                        active = formset.prefix
                        break
        
        context = {'formsets': formsets, 'media': media, 'active': active, 'errors': errors}
        context.update(kwargs)
        
        return super(FormsetsUpdateView, self).get_context_data(**context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if self.is_valid:
            form.save()  
            for formset in self.formsets:
                formset.save()

            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        msg = ""
        success_url = ""
        msg_dict = {'name': force_text(self.model._meta.verbose_name), 'obj': force_text(self.object)}
        if "_continue" in self.request.POST:
            msg = _('The %(name)s "%(obj)s" was changed successfully. You may edit it again below.') % msg_dict
            success_url = self.request.path
        else:
            msg = _('The %(name)s "%(obj)s" was changed successfully.') % msg_dict
            success_url = super(FormsetsUpdateView, self).get_success_url()   
            
        messages.add_message(self.request, level=messages.SUCCESS, message=msg, fail_silently=True)
        return success_url    
