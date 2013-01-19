"""
Utility functions for API purposes.
"""
import re

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


def parse_search_fields():
    FIELD_RANGE_REGEX = re.compile('^(?P<from>\d+)\-(?P<to>\d+)$')
    resp = {}
    val_query = request.json.get('query')
    if (val_query and isinstance(val_query, basestring) and
            '*' not in val_query):  # no special chars allowed
        resp['query_string'] = request.json.get('query').lower()
    elif request.json.get('query_prefix'):
        resp['query_string'] = (
            '%s*' % request.json.get('query_prefix').lower())

    resp['limit'] = request.json.get('limit') or 100

    if (request.json.get('max_distance_km') and
            request.json.get('max_distance_from')):
        resp['max_distance'] = (
            request.json.get('max_distance_km'),
            request.json.get('max_distance_from'))

    val_fields = request.json.get('fields')
    if (val_fields and isinstance(val_fields, dict)):
        resp['fields'] = {}
        for (key, val) in val_fields.iteritems():
            if val in (None, '', []):
                continue
            if isinstance(val, basestring):
                if '*' in val:  # no wildcards allowed here
                    continue
                re_match = FIELD_RANGE_REGEX.match(val)
                if re_match:  # we have a range
                    val = (re_match.group(1), re_match.group(2))
            resp['fields'][key] = val

    val_orderby = request.json.get('order_by')
    if (val_orderby and isinstance(val_orderby, basestring) and
            val_orderby[0] in ('-', '+')):
        resp['order_by'] = val_orderby

    return resp
