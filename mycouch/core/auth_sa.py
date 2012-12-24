"""
Module to provide plug-and-play authentication support for SQLAlchemy.
"""
import datetime
import hashlib
import memcache
import re
from sqlalchemy import Column, Integer, String, DateTime, Boolean, and_
from flaskext.auth import AuthUser, get_current_user_data
from flask import request, g
from mycouch import app


AUTH_TOKEN_MYCOUCH = re.compile(
    'MYC (?:apikey="(?P<apikey>[a-zA-Z0-9]+)"'
        '(?:, token="(?P<token>[a-zA-Z0-9]+)")?)?')


class MemcachedAuthHandler(object):
    client = None
    TOKEN_TIMEOUT = 60 * 60 * 24

    def __init__(self):
        self.client = memcache.Client(app.config['CACHE_MEMCACHED_SERVERS'])

    @staticmethod
    def _get_cache_key(token):
        return 'mycouch_auth:user:token(%s)' % token

    def get(self, token):
        return self.client.get(self._get_cache_key(token))

    def set(self, user):
        token = self.generate_token(user)
        user_data = {
            'username': user.username,
            'id': user.id,
        }
        self.client.set(self._get_cache_key(token), user_data, self.TOKEN_TIMEOUT)
        return token

    def renew(self, user, token):
        token = self._get_cache_key(token)
        user_data = self.client.get(token)
        self.client.set(token, user_data, self.TOKEN_TIMEOUT)

    @staticmethod
    def generate_token(user):
        return hashlib.md5('%s+++%s+++%s+++%s' % (
            'MYC', 'APIKEY', user.id,
            datetime.datetime.utcnow().isoformat())).hexdigest()


def get_user_class(declarative_base):
    """
    Factory function to create an SQLAlchemy User model with a declarative.
    base (for example db.Model from the Flask-SQLAlchemy extension).
    """
    class User(declarative_base, AuthUser):
        """
        Implementation of User for SQLAlchemy.
        """
        __abstract__ = True

        id = Column(Integer, primary_key=True)
        username = Column(String(80), unique=True, nullable=False)
        password = Column(String(120), nullable=False)
        salt = Column(String(80))
        role = Column(String(80))
        created = Column(DateTime(), default=datetime.datetime.utcnow)
        modified = Column(DateTime())
        is_active = Column(Boolean, default=True, nullable=False)

        def __init__(self, *args, **kwargs):
            super(User, self).__init__(*args, **kwargs)
            password = kwargs.get('password')
            if password is not None and not self.id:
                self.created = datetime.datetime.utcnow()
                # Initialize and encrypt password before first save.
                self.set_and_encrypt_password(password)

        def __getstate__(self):
            return {
                'id': self.id,
                'username': self.username,
                'role': self.role,
                'created': self.created,
                'modified': self.modified,
            }

        def authenticate(self, password):
            resp = super(User, self).authenticate(password)
            if resp:
                auth_handler = MemcachedAuthHandler()
                resp = auth_handler.set(self)
                g.auth_token = resp
            return resp

        @classmethod
        def get_current_token(cls):
            """
            Gets the currently logged user.
            """
            http_auth = request.headers.get('Authorization')
            if http_auth:
                re_match = AUTH_TOKEN_MYCOUCH.match(http_auth)
                if re_match:
                    re_match = re_match.groupdict()
                    return re_match.get('token')

        @classmethod
        def load_current_user(cls, apply_timeout=True):
            auth_handler = MemcachedAuthHandler()
            data = auth_handler.get(
                getattr(g, 'auth_token', None) or cls.get_current_token())
            if not data:
                return None
            return cls.query.filter(and_(
                cls.username == data['username'],
                cls.is_active)).one()

    return User
