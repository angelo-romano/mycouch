from flask import request, redirect, url_for, jsonify, make_response
from flask.views import MethodView
from flaskext.auth import login_required, logout, get_current_user_data
from flaskext.auth.models.sa import get_user_class
from geoalchemy import WKTSpatialElement
from mycouch import app, db
from mycouch.models import User, City
from functools import wraps

def only_this_user(fn):
    @wraps(fn)
    def fn2(cls, user, *args, **kwargs):
        logged_user = User.load_current_user()
        if user.id != logged_user.id:
            return ('', 401, [])
        else:
            return fn(cls, user, *args, **kwargs)
    return fn2


def user_by_id(fn):
    @wraps(fn)
    def fn2(cls, id, *args, **kwargs):
        user = (
            id if isinstance(id, db.Model)
            else User.query.filter_by(id=id).first())
        return fn(cls, user, *args, **kwargs)
    return fn2


class UserHandler(MethodView):
    __base_uri__ = '/users'
    __resource_name__ = 'users'

    def post(self):
        params = dict(
            first_name=request.json.get('first_name'),
            last_name=request.json.get('last_name'),
            email=request.json.get('email'),
            username=request.json.get('username'),
            password=request.json.get('password'))

        optional_params = dict(
            websites=request.json.get('websites') or '')

        if not all(params.values()):
            return (jsonify(error=True), 300, [])

        params.update(optional_params)

        user = User(**params)
        user.save(commit=True)
        return jsonify(user.serialized)


class UserByIDHandler(MethodView):
    __base_uri__ = '/users/<int:id>'
    __resource_name__ = 'users_one'

    @classmethod
    @user_by_id
    @only_this_user
    def _get(cls, user):
        return jsonify(user.serialized)

    @classmethod
    @user_by_id
    @only_this_user
    def _patch(cls, user):
        params = dict(
            first_name=request.json.get('first_name'),
            last_name=request.json.get('last_name'),
            email=request.json.get('email'),
            websites=request.json.get('websites') or '')

        params.update(optional_params)

        for (key, val) in params.iteritems():
            curval = getattr(user, key, None)
            if curval != val:
                setattr(user, key, val)

        user.save(commit=True)
        return jsonify(user.serialized)

    @login_required()
    def get(self, id):
        return self._get(id)

    @login_required()
    def patch(self, id):
        return self._patch(id)
