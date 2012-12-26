"""
Module to provide plug-and-play authentication support for SQLAlchemy.
"""
import datetime
import hashlib
import memcache
import re
from flask import g, request
from mycouch import app
from functools import wraps


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
        self.client.set(self._get_cache_key(token),
                        user_data, self.TOKEN_TIMEOUT)
        return token

    def renew(self, user, token):
        token = self._get_cache_key(token)
        user_data = self.client.get(token)
        self.client.set(token, user_data, self.TOKEN_TIMEOUT)

    def unset(self, token):
        self.client.delete(self._get_cache_key(token))

    @staticmethod
    def generate_token(user):
        return hashlib.md5('%s+++%s+++%s+++%s' % (
            'MYC', 'APIKEY', user.id,
            datetime.datetime.utcnow().isoformat())).hexdigest()


def get_current_token():
    """
    Gets the currently logged user.
    """
    http_auth = request.headers.get('Authorization')
    if http_auth:
        re_match = AUTH_TOKEN_MYCOUCH.match(http_auth)
        if re_match:
            re_match = re_match.groupdict()
            return re_match.get('token')


def login_required():
    def decorator(fn):
        @wraps(fn)
        def fn2(*args, **kwargs):
            auth = get_request_token()
            if auth:
                return fn(*args, **kwargs)
            return ('', 401, [])
        return fn2
    return decorator


def get_request_token():
    return get_current_token() or getattr(g, 'auth_token', None)


def logout():
    token = get_request_token()
    g.auth_token = None
    auth_handler = MemcachedAuthHandler()
    auth_handler.unset(token)
