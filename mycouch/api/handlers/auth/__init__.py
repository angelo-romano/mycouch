from flask import request, redirect, url_for, jsonify, make_response
from flask.views import MethodView
from flaskext.auth import login_required, logout, get_current_user_data
from flaskext.auth.models.sa import get_user_class
from geoalchemy import WKTSpatialElement
from mycouch import app, db
from mycouch.api.handlers.users import UserByIDHandler
from mycouch.models import User, City


class AuthHandler(MethodView):
    __base_uri__ = '/auth'
    __resource_name__ = 'auth'

    def post(self):
        username, password = (
            request.json.get('username'), request.json.get('password'))
        user = User.query.filter_by(username=username).first()
        if not user:
            return ('', 401, [])
        if user.authenticate(password):
            return UserByIDHandler._get(user)
        return ('', 401, [])

    def delete(self):
        logout()
        return jsonify(success=True)
