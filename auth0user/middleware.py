from django.conf import settings


def auth0user_middleware(get_response):
    def middleware(request):
        if getattr(request, 'user') and not request.user.is_authenticated():
            redirect_host = ''.join([request.scheme, '://', request.get_host()])
            request.auth0 = {
                'client_id': settings.AUTH0_CLIENT_ID,
                'domain': settings.AUTH0_DOMAIN,
                'redirect_host': redirect_host
            }
        response = get_response(request)
        return response
    return middleware
