=============================
django-auth0user
=============================

.. image:: https://badge.fury.io/py/django-auth0user.png
    :target: https://badge.fury.io/py/django-auth0user

.. image:: https://travis-ci.org/bretth/django-auth0user.png?branch=master
    :target: https://travis-ci.org/bretth/django-auth0user

An Django abstract User Model backed by Auth0 that allows per-site users and permissions and uses email for username. Warning - this is alpha quality.

Overview
--------

This abstract Django model allows for a non-unique email-username User model. Sounds crazy right. Let me demonstrate why that's useful. 

Local users are unique *per-site* (using the django sites framework) so this allows users to be added to multiple sites, have separate permissions (and potentially site preferences), and use a unique Auth0 account to authenticate against. Traditionally the user profile would be kept in a separate model. In this case the user profile is kept on Auth0 and just cached and proxied locally. When implementing the custom User model it may be extended to allow for site specific user preferences.

The main caveats are that to maintain compatibility and functionality for offline development and testing, email and password are *also* stored locally as per the traditional user model. 

When developing your application the auth0 profile should always be treated as the master data. It **is** feasible (and desirable) that a change could be made to the auth0 account or backend account that your app knows nothing about, so where possible your app should treat the Auth0 email address as the authoratitive address and just sync on login or have a workflow for email change. The same applies to passwords. If the auth0 password is updated without the app's knowledge there is no way to get that updated password - so really the local passwords are just for the benefit of development not as a production alternative for auth0. 

Also to maintain compatibility, unless you expressly specify a site id, the default `settings.SITE_ID` is always assumed when querying or creating users.

Finally, The user model `first_name` and `last_name` attributes are kept for backward compatibility but are actually now just a proxy for the network auth0 profile `given_name` and `family_name`. 

It makes sense now right! Local site profiles and permissions with the user's actual account handled by Auth0, or whatever Auth0 backend you want (Github, Microsoft, Google, Facebook etc).


Installation
------------

Install django-auth0user::

    pip install django-auth0user

Add auth0user ahead of *django.contrib.auth* in your INSTALLED_APPS, and create an app that will hold your custom user model. You'll also need to add the django sites app::

    # settings.py 

    INSTALLED_APPS = [

        'auth0user',

        'django.contrib.admin',
        'django.contrib.auth',

        'django.contrib.sites', 
        'djangoproject.apps.siteuser'  # add your custom user model app
        
    ]

    SITE_ID = 1

What that gives you is a replacement `createsuperuser` management command and an admin auth0 login template from auth0user if you are using app template discovery. 

Add sites and auth0user middleware::

    MIDDLEWARE = [
    ...
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'auth0user.middleware.auth0user_middleware',
    ]

Also in the settings file you'll need to silence an error for a non-unique user model::

    SILENCED_SYSTEM_CHECKS = [
        "auth.E003",  # non-unique User
    ]

You'll need your Auth0 secrets and a custom user model::

    AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
    AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
    AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')
    AUTH0_CONNECTION = os.getenv('AUTH0_CONNECTION')
    AUTH0_JWT = os.getenv('AUTH0_JWT')

    AUTH_USER_MODEL = 'siteuser.User'  # Your custom user model

Finally create the app with your own custom User model that inherits the auth0user abstract SiteUser and sprinkle your magic site specific profile attributes on it::
    
    # models.py in djangoproject/apps/siteuser example

    from auth0plus.models import SiteUser

    class User(SiteUser):
        pass


Because it is a custom user model Django requires you make the migration first before any other migration::

    ./manage.py makemigrations siteuser
    ./manage.py migrate

Create your superuser (creates or re-uses an existing Auth0 user):

    ./manage.py createsuperuser


Running Tests
--------------

Does the code actually work? Probably not.

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install -r requirements-test.txt
    (myenv) $ pytest

Credits
---------

Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-djangopackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-djangopackage`: https://github.com/pydanny/cookiecutter-djangopackage
