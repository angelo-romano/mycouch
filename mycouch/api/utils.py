"""
Utility functions for API purposes.
"""
import re
from flask import abort, g, request
from mycouch import app
from mycouch.api.auth import get_request_token
from mycouch.core.serializers import json_dumps
from mycouch.models import User
from functools import wraps


def get_logged_user():
    """
    Gets the currently logged user.
    """
    return User.load_current_user(get_request_token())


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
