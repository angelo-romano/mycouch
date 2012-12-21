"""
Utility functions for API purposes.
"""
from flask import abort, g, request
from mycouch import app
from mycouch.core.serializers import json_dumps


def user_required(f):
    """
    Checks whether user is logged in or raises error 401.
    """
    def decorator(*args, **kwargs):
        if not g.user:
            abort(401)
        return f(*args, **kwargs)
    return decorator


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
        json_dumps(dict(val), indent=None if request.is_xhr else 2),
        mimetype='application/json')
