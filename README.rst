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

The Django auth model backend is of a time when django projects where more monolithic in nature and not complimentary to native apps. The backend is tightly coupled to the project which makes it awkward to use as an authentication source for other projects or platforms. Additionally the user permissions are tied to the user which makes them global across multi-site setups which may not be desirable. 

Although Django makes it possible to do our own backend and permissions, this project aims to retain the auth model backend but loosely couple the user to your Django project, leveraging Auth0 as the authentication and identity store, while allowing for site specific permissions and user preferences. It does this through a custom abstract model which adds a site attribute to the user and makes the username unique *per-site*, while linking to a global auth0 user.

The main caveats are that to maintain compatibility and functionality for offline development and testing, email and password can *also* be stored locally as per the traditional user model - but it is intended that Auth0 be the master data for all global user attributes. 

Also to maintain compatibility, unless you expressly specify a site id, the default `settings.SITE_ID` is always assumed when querying or creating users.

Finally, The user model *first_name* and *last_name* attributes are kept for backward compatibility but are actually now just a proxy for the auth0 stored profile *given_name* and *family_name*. 


Installation
------------

Install django-auth0user::

    pip install git+https://github.com/bretth/django-auth0user#egg=auth0user

Add *auth0user* ahead of *django.contrib.auth* in your INSTALLED_APPS, and create an app that will hold your custom user model. You'll also need to add the django sites app::

    # settings.py 

    INSTALLED_APPS = [

        'auth0user',

        'django.contrib.admin',
        'django.contrib.auth',

        'django.contrib.sites', 
        'djangoproject.apps.siteuser'  # add your custom user model app
        
    ]

    SITE_ID = 1

What that gives you is a replacement *createsuperuser* management command and an admin auth0 login template from auth0user if you are using app template discovery. 

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

Finally create the app with your custom User model that inherits the auth0user abstract SiteUser and sprinkle your magic site specific profile attributes on it::
    
    # models.py in djangoproject/apps/siteuser example

    from auth0plus.models import SiteUser

    class User(SiteUser):
        pass


Because it is a custom user model Django requires you make the migration first before any other migration::

    ./manage.py makemigrations siteuser
    ./manage.py migrate

Create your superuser (creates or re-uses an existing Auth0 user)::

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
