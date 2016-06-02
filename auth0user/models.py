# -*- coding: utf-8 -*-

import logging

from auth0plus.exceptions import Auth0Error
from auth0plus.management import Auth0
from django.core.cache import cache
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.core.mail import send_mail
from django.contrib.auth import password_validation
from django.contrib.auth.hashers import (
    check_password, is_password_usable, make_password,
)
from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.translation import ugettext_lazy as _

from model_utils.fields import AutoCreatedField, AutoLastModifiedField

logger = logging.getLogger(__name__)


class Profile(object):
    
    _Auth0User = Auth0(
        settings.AUTH0_DOMAIN,
        settings.AUTH0_JWT,
        client_id=settings.AUTH0_CLIENT_ID,
        default_connection=settings.AUTH0_CONNECTION).users
    
    def __init__(self, auth0user=None):

        if auth0user:
            kwargs = auth0user.as_dict()
        else:
            kwargs = {
                'email': '',
                'user_metadata': {},
                'app_metadata': {},
            }
        self._auth0user = auth0user

        self.__dict__.update(kwargs)

    @classmethod
    def _get_cache_key(cls, auth0_id):
        return 'auth0user.userprofile.%s' % auth0_id

    @classmethod
    def get(cls, auth0_id=None):
        if not auth0_id:
            return cls()
        key = cls._get_cache_key(auth0_id)
        auth0user = cache.get(key)
        if not auth0user:
            try:
                auth0user = cls._Auth0User.get(auth0_id)
                cache.set(key, auth0user, settings.AUTH0_PROFILE_CACHE)
            except (cls.objects.DoesNotExist, Auth0Error):
                logger.error("UserProfile Could not get auth0 user", exc_info=True)
                auth0user = None

        userprofile = cls(auth0user)
        return userprofile

    @property
    def given_name(self):
        """
        Given name may be set externally to Auth0 which takes precedance over user_metadata
        """
        return self.__dict__.get('given_name', self.user_metadata.get('given_name', ''))

    @given_name.setter
    def given_name(self, value):
        self.user_metadata['given_name'] = value

    @property
    def family_name(self):
        """
        Family name may be set externally to Auth0 which takes precedance over user_metadata
        """
        return self.__dict__.get('family_name', self.user_metadata.get('family_name', ''))

    @family_name.setter
    def family_name(self, value):
        self.user_metadata['family_name'] = value

    def save(self):
        if self._auth0user:
            for key in self._auth0user._updatable:
                try:
                    value = getattr(self, key)
                except AttributeError:
                    continue
                setattr(self._auth0user, key, value)
            cache.set(
                self._get_cache_key(self._auth0user.user_id),
                self._auth0user,
                settings.AUTH0_PROFILE_CACHE)
            self._auth0user.save()


class SiteUserManager(BaseUserManager):

    """ Custom manager for User."""

    _Auth0User = Auth0(
        settings.AUTH0_DOMAIN,
        settings.AUTH0_JWT,
        client_id=settings.AUTH0_CLIENT_ID,
        default_connection=settings.AUTH0_CONNECTION).users

    def _create_user(self, email, password, **extra_fields):
        """ Create and save an EmailUser with the given email and password.

        :param str email: user email
        :param str password: user password
        :param bool is_staff: whether user staff or not
        :param bool is_superuser: whether user admin or not
        :return custom_user.models.EmailUser user: user
        :raise ValueError: email is not set

        """
        if not email:
            raise ValueError('The email must be set')
        auth0user = extra_fields.pop('auth0user', None)
        email_verified = extra_fields.pop('email_verified', False)
        if not auth0user:
            auth0user, created = self._Auth0User.get_or_create(
                defaults={
                    'email_verified': email_verified,
                    'password': password,
                    'user_metadata': {
                        'given_name': extra_fields.get('first_name', ''),
                        'family_name': extra_fields.get('last_name', '')}
                },
                email=email)

        user = self.model(auth0_id=auth0user.user_id, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """ Create and save an EmailUser with the given email and password.

        :param str email: user email
        :param str password: user password
        :return custom_user.models.EmailUser user: regular user

        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('site_id', getattr(settings, 'SITE_ID', 1))
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('site_id', getattr(settings, 'SITE_ID', 1))
        extra_fields.setdefault('email_verified', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, auth0_id, site_id=settings.SITE_ID):
        """
        Overrides BaseUserManager to add site_id
        """
        return self.get(**{self.model.USERNAME_FIELD: auth0_id, 'site_id': site_id})


class SiteUser(models.Model):

    """
    Replacement user model for standard Django User which uses auth0 and sites.
    """

    auth0_id = models.CharField(_('auth0 user id'), max_length=36, editable=False)
    email = models.EmailField(_('email address'), max_length=150, editable=False)
    password = models.CharField(_('password'), max_length=128)
    
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    site = models.ForeignKey(Site, blank=True, default=settings.SITE_ID)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    last_login = models.DateTimeField(_('last login'), blank=True, null=True)
    created = AutoCreatedField(_('created'))
    modified = AutoLastModifiedField(_('modified'))

    objects = SiteUserManager()
    on_site = CurrentSiteManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        abstract = True
        unique_together = ('auth0_id', 'site')
        verbose_name = _('site user')
        verbose_name_plural = _('site users')

    # Modified from django.contrib.auth.base_models #
    def get_username(self):
        "Return the identifying username for this User"
        return getattr(self, self.USERNAME_FIELD)

    def __init__(self, *args, **kwargs):
        super(SiteUser, self).__init__(*args, **kwargs)
        # Stores the raw password if set_password() is called so that it can
        # be passed to password_changed() after the model is saved.
        self._password = None
        self._save_profile = False

    def __str__(self):
        return self.get_username()

    def save(self, *args, **kwargs):
        self.profile.save()
        super(SiteUser, self).save(*args, **kwargs)
        if self._password is not None:
            password_validation.password_changed(self._password, self)
            self._password = None

    def natural_key(self):  # also includes site_id
        return (self.get_username(), self.site_id)

    @property
    def is_anonymous(self):
        """
        Always return False. This is a way of comparing User objects to
        anonymous users.
        """
        return False

    @property
    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        """
        return True

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self._password = raw_password
        self.profile.password = raw_password

    def check_password(self, raw_password):
        """
        Return a boolean of whether the raw_password was correct. Handles
        hashing formats behind the scenes.
        """
        def setter(raw_password):
            self.set_password(raw_password)
            # Password hash upgrades shouldn't be considered password changes.
            self._password = None
            self.save(update_fields=["password"])
        return check_password(raw_password, self.password, setter)

    def set_unusable_password(self):
        # Set a value that will never be a valid hash
        self.password = make_password(None)

    def has_usable_password(self):
        return is_password_usable(self.password)

    def get_session_auth_hash(self):
        """
        Return an HMAC of the password field.
        """
        key_salt = "django.contrib.auth.models.AbstractBaseUser.get_session_auth_hash"
        return salted_hmac(key_salt, self.password).hexdigest()
    # End section modified from django.contrib.auth.base_models #

    @property
    def first_name(self):
        return self.profile.given_name

    @first_name.setter
    def first_name(self, value):
        self.profile.given_name = value
    
    @property
    def last_name(self):
        return self.profile.family_name

    @last_name.setter
    def last_name(self, value):
        self.profile.family_name = value

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

    @property
    def profile(self):
        try:
            return self._profile
        except AttributeError:
            pass
        self._profile = Profile.get(self.auth0_id)
        return self._profile

    def email_user(self, subject, message, from_email=None, **kwargs):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)

    def change_email(self, new_email):

        try:
            self.profile.email = new_email
            self.profile.save()
        except self.profile._Auth0User.DoesNotExist:
            pass
        self.email = new_email
        self.modified = timezone.now()
        self.objects.filter(email=self.email).update(email=new_email, modified=self.modified)
