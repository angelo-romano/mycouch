"""
Utility functions for API purposes.
"""
import re
from flask import abort, g, request
from mycouch import app
from mycouch.core.serializers import json_dumps
from mycouch.models import User
from functools import wraps


AUTH_TOKEN_MYCOUCH = re.compile(
    'MYC (?:apikey="(?P<apikey>[a-zA-Z0-9]+)"'
    '(?:, token="(?P<token>[a-zA-Z0-9]+)")?)?')


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


def user_required(f):
    """
    Checks whether user is logged in or raises error 401.
    """
    def decorator(*args, **kwargs):
        if not g.user:
            abort(401)
        return f(*args, **kwargs)
    return decorator


def get_logged_user():
    """
    Gets the currently logged user.
    """
    token = get_request_token()
    return User.load_current_user(get_request_token())


def get_request_token():
    http_auth = request.headers.get('Authorization')
    if http_auth:
        re_match = AUTH_TOKEN_MYCOUCH.match(http_auth)
        if re_match:
            re_match = re_match.groupdict()
            resp = re_match.get('token')
            if resp:
                return resp
    return getattr(g, 'auth_token', None)


def make_error_dict(error_list):
    """
    Builds the error dict for a response.
    """
    resp = {
        'error': bool(error_list)
    }
    if error_list:
        resp['error_list'] = error_list
    return resp


def jsonify(val):
    """
    Custom implementation of jsonify, to use the custom JSON dumps function.
    """
    return app.response_class(
        json_dumps(val, indent=None if request.is_xhr else 2),
        mimetype='application/json')
