import json

import requests

from django.conf import settings
from django.contrib.auth import _get_backends, get_user_model, login
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse


def authenticate(auth0_id):
    """
    If the given credentials are valid, return a User object.
    """
    for backend, backend_path in _get_backends(return_tuples=True):
        UserModel = get_user_model()
        try:
            user = UserModel._default_manager.get_by_natural_key(auth0_id)
            if backend.user_can_authenticate(user):
                # Annotate the user object with the path of the backend.
                user.backend = backend_path
                return user
        except UserModel.DoesNotExist:
            pass


def alogin(request):
    code = request.GET.get('code', None)
    current_app = request.resolver_match.namespace
    # default to the admin index
    admin_url = reverse('admin:index', current_app=current_app)
    redirect_next = request.GET.get('state', admin_url)
    if not code:
        return redirect_to_login(
            request.get_full_path(),
            reverse('admin:login', current_app=current_app))
    elif request.user.is_authenticated():
        return redirect(redirect_next)

    json_header = {'content-type': 'application/json'}
    token_url = "https://{domain}/oauth/token".format(domain=settings.AUTH0_DOMAIN)
    redirect_path = reverse('auth0user:alogin', current_app=request.resolver_match.namespace)
    token_payload = {
        'client_id': settings.AUTH0_CLIENT_ID,
        'client_secret': settings.AUTH0_CLIENT_SECRET,
        'redirect_uri': ''.join([request.auth0.get('redirect_host'), redirect_path]),
        'code': code,
        'grant_type': 'authorization_code'
    }
    token_info = requests.post(
        token_url, data=json.dumps(token_payload), headers=json_header).json()

    user_url = "https://{domain}/userinfo?access_token={access_token}".format(
        domain=settings.AUTH0_DOMAIN, access_token=token_info['access_token'])
    user_info = requests.get(user_url).json()

    # log the user in...
    user = authenticate(user_info.get('user_id', None))
    if user:
        login(request, user)
        return redirect(redirect_next)
    raise PermissionDenied
