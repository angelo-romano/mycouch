from flask import request
from flask.views import MethodView
from flaskext.auth import logout
from mycouch.api.handlers.users import UserByIDHandler
from mycouch.api.utils import jsonify
from mycouch.models import User


class AuthHandler(MethodView):
    __base_uri__ = '/auth'
    __resource_name__ = 'auth'

    def post(self):
        username, password = (
            request.json.get('username'), request.json.get('password'))
        user = User.query.filter_by(username=username).first()
        if not user:
            return ('', 401, [])
        resp = user.authenticate(password)
        if resp:
            return UserByIDHandler._get(user)
        return ('', 401, [])

    def delete(self):
        logout()
        return jsonify(success=True)
