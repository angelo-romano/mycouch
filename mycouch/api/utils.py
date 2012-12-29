"""
Utility functions for API purposes.
"""
from flask import abort, request
from mycouch import app
from mycouch.api.auth import get_request_token
from mycouch.core.serializers import json_dumps
from mycouch.core.db import Base
from mycouch.models import User
from functools import wraps


def get_logged_user():
    """
    Gets the currently logged user.
    """
    return User.load_current_user(get_request_token())


def build_error_dict(error_list):
    """
    Builds the error dict for a response.
    """
    resp = {
        'error': bool(error_list)
    }
    if error_list:
        resp['error_list'] = error_list
    return resp


def jsonify(*args, **kwargs):
    """
    Custom implementation of jsonify, to use the custom JSON dumps function.
    """
    if args:
        if len(args) == 1:
            val = args[0]
        else:
            val = args
    else:
        val = kwargs
    return app.response_class(
        json_dumps(val, indent=None if request.is_xhr else 2),
        mimetype='application/json')


def get_filter_dict(params, fields_only=None):
    return dict((k[2:], v) for (k, v) in params.iteritems()
                if k.startswith('f:')
                and (not fields_only or k[2:] in fields_only))


def model_by_id(model_class):
    def decorator(fn):
        @wraps(fn)
        def fn2(cls, id, *args, **kwargs):
            instance = (
                id if isinstance(id, Base)
                else model_class.query.filter_by(id=id).first())
            return fn(cls, instance, *args, **kwargs)
        return fn2
    return decorator
