
def get_request_param(request, name, default=None):
    return request.POST.get(name, request.GET.get(name, default))
