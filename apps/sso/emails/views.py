# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.utils.encoding import force_text
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import ListView, DeleteView, DetailView, CreateView
from django.views.generic.detail import SingleObjectMixin
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.contrib import messages

import logging
logger = logging.getLogger(__name__)
