# -*- coding: utf-8 -*-
from django.views.generic import UpdateView
from django.contrib.staticfiles.templatetags.staticfiles import static
from django import forms

from sso.forms.helpers import ErrorList

import logging
logger = logging.getLogger(__name__)

class FormsetsUpdateView(UpdateView):
    
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
