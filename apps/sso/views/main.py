# -*- coding: utf-8 -*-
from collections import OrderedDict

from django.db import models
from django.db.models.expressions import OrderBy
from django.utils.encoding import python_2_unicode_compatible, force_text
from django.utils.html import format_html
from django.utils.http import urlencode

# Changelist settings
# ALL_VAR = 'all'
ORDER_VAR = 'o'
# ORDER_TYPE_VAR = 'ot'
PAGE_VAR = 'p'
PAGE_SIZE_VAR = 's'
SEARCH_VAR = 'q'
# TO_FIELD_VAR = 't'
# IS_POPUP_VAR = 'pop'
ERROR_FLAG = 'e'

IGNORED_PARAMS = (  
    # ALL_VAR,    
    ORDER_VAR,   # ORDER_TYPE_VAR,    
    SEARCH_VAR,  # IS_POPUP_VAR,  #TO_FIELD_VAR   
)

# Text to display within change-list table cells if the value is blank.
# EMPTY_CHANGELIST_VALUE = ugettext_lazy('(None)')
    
    
class ChangeList(object):
    
    def __init__(self, request, model, list_display, default_ordering=None, orderd_columns=None):
        if default_ordering is None:
            default_ordering = []
        if orderd_columns is None:
            orderd_columns = []
        self.opts = model._meta
        self.lookup_opts = self.opts
        self.list_display = list_display
        self.orderd_columns = orderd_columns
        self.params = dict(request.GET.items())
        # if PAGE_VAR in self.params:
        #    del self.params[PAGE_VAR]
        if ERROR_FLAG in self.params:
            del self.params[ERROR_FLAG]
        self.default_ordering = default_ordering
        
    def get_query_string(self, new_params=None, remove=None):
        if new_params is None: 
            new_params = {}
        if remove is None: 
            remove = []
        p = self.params.copy()
        for r in remove:
            for k in list(p):
                if k.startswith(r):
                    del p[k]
        for k, v in new_params.items():
            if v is None:
                if k in p:
                    del p[k]
            else:
                p[k] = v
        return '?%s' % urlencode(sorted(p.items()))
    
    def label_for_field(self, field_name):
        """
        if the field is from the model it's sortable otherwise check for a attribute
        sortable.
        """
        try:
            field = self.lookup_opts.get_field(field_name)
            return field.verbose_name, {"sortable": True}
        except models.FieldDoesNotExist:
            label = [field_name, {"sortable": False}]
            if hasattr(field_name, 'verbose_name'):
                label[0] = field_name.verbose_name
            if hasattr(field_name, 'sortable'):
                label[1] = {"sortable": field_name.sortable}
            
            return tuple(label) 
            
    def get_ordering_field(self, field_name):
        if hasattr(field_name, 'ordering_field'):
            return field_name.ordering_field
        else:
            return force_text(field_name)

    def get_ordering(self, request, queryset):
        """
        Returns the list of ordering fields for the change list.
        First we check the get_ordering() method in model admin, then we check
        the object's default ordering. Then, any manually-specified ordering
        from the query string overrides anything. Finally, a deterministic
        order is guaranteed by ensuring the primary key is used as the last
        ordering field.
        """
        params = self.params
        ordering = self._get_default_ordering()
        if ORDER_VAR in params:
            # Clear ordering and used params
            ordering = []
            order_params = params[ORDER_VAR].split('.')
            for p in order_params:
                try:
                    none, pfx, idx = p.rpartition('-')  # @UnusedVariable
                    field_name = self.list_display[int(idx)]
                    order_field = self.get_ordering_field(field_name)
                    if not order_field:
                        continue  # No 'admin_order_field', skip it
                    try:  # OrderBy Expression
                        if pfx == '-':
                            order_field.desc()
                        else:
                            order_field.asc()
                    except AttributeError:
                        order_field = pfx + order_field

                    ordering.append(order_field)
                except (IndexError, ValueError):
                    continue  # Invalid ordering specified, skip it.

        # Add the given query's ordering fields, if any.
        ordering.extend(queryset.query.order_by)
        
        return ordering

    def _get_default_ordering(self):
        return self.default_ordering

    def get_ordering_field_columns(self):
        """
        Returns a OrderedDict of ordering field column numbers and asc/desc
        """

        # We must cope with more than one column having the same underlying sort
        # field, so we base things on column numbers.
        ordering = self._get_default_ordering()
        ordering_fields = OrderedDict()
        if ORDER_VAR not in self.params:
            # for ordering specified on default_ordering or model Meta, we don't know
            # the right column numbers absolutely, because there might be more
            # than one column associated with that ordering, so we guess.
            for field in ordering:
                # field can be in the form '-fieldname' or an OrderBy Expression
                try:  # OrderBy Expression
                    if field.descending:
                        order_type = 'desc'
                    else:
                        order_type = 'asc'
                    field = field.expression.name
                except AttributeError:
                    if field.startswith('-'):
                        order_type = 'desc'
                    else:
                        order_type = 'asc'
                    field = field[1:]
                for index, attr in enumerate(self.list_display):
                    ordering_field = self.get_ordering_field(attr)
                    try:  # OrderBy Expression
                        ordering_field = ordering_field.expression.name
                    except AttributeError:
                        pass

                    if ordering_field == field:
                        ordering_fields[index] = order_type
                        break
        else:
            for p in self.params[ORDER_VAR].split('.'):
                none, pfx, idx = p.rpartition('-')  # @UnusedVariable
                try:
                    idx = int(idx)
                except ValueError:
                    continue  # skip it
                ordering_fields[idx] = 'desc' if pfx == '-' else 'asc'
        return ordering_fields
    
    def result_headers(self):
        """
        Generates the list column headers.
        """
        ordering_field_columns = self.get_ordering_field_columns()
        for i, field_name in enumerate(self.list_display):
            text, attr = self.label_for_field(field_name)
            if attr:
                sortable = attr.get('sortable', False)
                if not sortable:
                    # Not sortable
                    yield {
                        "text": text,
                        "sortable": False,
                    }
                    continue
    
            # OK, it is sortable if we got this far
            th_classes = ['sortable']
            order_type = ''
            new_order_type = 'asc'
            sort_priority = 0
            sorted = False  # @ReservedAssignment
            # Is it currently being sorted on?
            if i in ordering_field_columns:
                sorted = True  # @ReservedAssignment
                order_type = ordering_field_columns.get(i).lower()
                sort_priority = list(ordering_field_columns).index(i) + 1
                th_classes.append('sorted %sending' % order_type)
                new_order_type = {'asc': 'desc', 'desc': 'asc'}[order_type]
    
            # build new ordering param
            o_list_primary = []  # URL for making this field the primary sort
            o_list_remove = []  # URL for removing this field from sort
            o_list_toggle = []  # URL for toggling order type for this field
            # make_qs_param =  lambda t, n: ('-' if t == 'desc' else '') + str(n)
            
            def make_qs_param(t, n):
                return ('-' if t == 'desc' else '') + str(n)
            
            for j, ot in ordering_field_columns.items():
                if j == i:  # Same column
                    param = make_qs_param(new_order_type, j)
                    # We want clicking on this header to bring the ordering to the
                    # front
                    o_list_primary.insert(0, param)
                    o_list_toggle.append(param)
                    # o_list_remove - omit
                else:
                    param = make_qs_param(ot, j)
                    o_list_primary.append(param)
                    o_list_toggle.append(param)
                    o_list_remove.append(param)
    
            if i not in ordering_field_columns:
                o_list_primary.insert(0, make_qs_param(new_order_type, i))
    
            yield {
                "text": text,
                "sortable": True,
                "sorted": sorted,
                "ascending": order_type == "asc",
                "sort_priority": sort_priority,
                "url_primary": self.get_query_string({ORDER_VAR: '.'.join(o_list_primary)}),
                "url_remove": self.get_query_string({ORDER_VAR: '.'.join(o_list_remove)}),
                "url_toggle": self.get_query_string({ORDER_VAR: '.'.join(o_list_toggle)}),
                "class_attrib": format_html(' class="{0}"', ' '.join(th_classes)) if th_classes else '',
            }


@python_2_unicode_compatible
class FilterItem(object):
    def __init__(self, item_tuple):
        self.item_tuple = item_tuple
    
    @property
    def pk(self):
        return self.item_tuple[0]
    
    def __str__(self):
        return u"%s" % self.item_tuple[1]


class OrderByWithNulls(OrderBy):
    """
    appends NULLS LAST or NULLS FIRST
    can be used for ordering_field in list_display items
    """
    def as_sql(self, compiler, connection):
        connection.ops.check_expression_support(self)
        expression_sql, params = compiler.compile(self.expression)
        placeholders = {'expression': expression_sql, 'ordering': 'DESC NULLS LAST' if self.descending else 'ASC NULLS FIRST'}
        return (self.template % placeholders).rstrip(), params


