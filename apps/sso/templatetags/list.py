from django.template import Library
from django.utils.html import format_html
from sso.views.main import PAGE_VAR

register = Library()

DOT = '.'


@register.simple_tag(takes_context=True)
def selected(context, param_name, param_value):
    if context.request.GET.get(param_name) == str(param_value):
        return 'selected'
    return ''


@register.simple_tag
def query_string(cl, new_param_name, new_param_value, remove=None):
    if remove:
        remove = remove.split(',')
    return cl.get_query_string(new_params={new_param_name: new_param_value}, remove=remove)


@register.simple_tag
def paginator_info(page):
    paginator = page.paginator
    entries_from = (
        (paginator.per_page * (page.number - 1)) + 1) if paginator.count > 0 else 0
    entries_to = entries_from - 1 + paginator.per_page
    if paginator.count < entries_to:
        entries_to = paginator.count
    return '%s - %s' % (entries_from, entries_to)


@register.simple_tag
def paginator_number(page, i, cl):
    """
    Generates an individual page index link in a paginated list.
    """
    if i == DOT:
        return format_html('<li class="disabled"><a href="#">&hellip;</a></li>')
    elif i == page.number:
        return format_html('<li class="active"><a href="#">{0}</a></li>', i)
    else:
        return format_html('<li class=""><a href="{0}" >{1}</a></li>', cl.get_query_string({PAGE_VAR: i}), i)


@register.inclusion_tag('include/pagination.html')
def pagination(page, cl):
    """
    Generates the series of links to the pages in a paginated list.
    """
    paginator, page_num = page.paginator, page.number

    pagination_required = (paginator.num_pages > 1)
    if not pagination_required:
        page_range = []
    else:
        ON_EACH_SIDE = 3
        ON_ENDS = 2

        # If there are 10 or fewer pages, display links to every page.
        # Otherwise, do some fancy
        if paginator.num_pages <= 10:
            page_range = range(1, paginator.num_pages + 1)
        else:
            # Insert "smart" pagination links, so that there are always ON_ENDS
            # links at either end of the list of pages, and there are always
            # ON_EACH_SIDE links at either end of the "current page" link.
            page_range = []
            if page_num > (ON_EACH_SIDE + ON_ENDS):
                page_range.extend(range(1, ON_EACH_SIDE))
                page_range.append(DOT)
                page_range.extend(range(page_num - ON_EACH_SIDE, page_num))
            else:
                page_range.extend(range(1, page_num))
            if page_num < (paginator.num_pages - ON_EACH_SIDE - ON_ENDS):
                page_range.extend(range(page_num, page_num + ON_EACH_SIDE + 1))
                page_range.append(DOT)
                page_range.extend(range(paginator.num_pages - ON_ENDS + 1, paginator.num_pages + 1))
            else:
                page_range.extend(range(page_num, paginator.num_pages + 1))

    return {
        'page': page,
        'pagination_required': pagination_required,
        'page_range': page_range,
        'cl': cl
    }
