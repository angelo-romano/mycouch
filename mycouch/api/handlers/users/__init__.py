from flask import request
from flask.views import MethodView
from mycouch import db
from mycouch.api.auth import login_required, get_request_token
from mycouch.api.utils import jsonify, get_logged_user
from mycouch.models import User
from functools import wraps


def only_this_user(fn):
    @wraps(fn)
    def fn2(cls, user, *args, **kwargs):
        logged_user = get_logged_user()
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
            city_id=request.json.get('city_id'),
            websites=request.json.get('websites') or '')

        if not all(params.values()):
            return (jsonify(error=True), 400, [])

        params.update(optional_params)
        user = User(**params)
        user.save(commit=True)
        return UserByIDHandler._get(user)


class UserByIDHandler(MethodView):
    __base_uri__ = '/users/<int:id>'
    __resource_name__ = 'users_one'

    @classmethod
    @user_by_id
    @only_this_user
    def _get(cls, user):
        expand_rels = request.args.get('expand')
        if expand_rels:
            expand_rels = filter(lambda o: o.lower().strip(),
                                 expand_rels.split(','))
            user.force_serialize(expand_rels)
        resp = user.serialized
        resp['token'] = get_request_token()
        return jsonify(resp)

    @classmethod
    @user_by_id
    @only_this_user
    def _patch(cls, user):
        params = dict(
            first_name=request.json.get('first_name'),
            last_name=request.json.get('last_name'),
            email=request.json.get('email'),
            city_id=request.json.get('city_id'),
            websites=request.json.get('websites') or '')

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
