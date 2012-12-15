from flask import request, redirect, url_for, jsonify, make_response
from flask.views import MethodView
from flaskext.auth import login_required, logout, get_current_user_data
from flaskext.auth.models.sa import get_user_class
from geoalchemy import WKTSpatialElement
from mycouch import app, db
from mycouch.api.handlers.users import UserByIDHandler
from mycouch.models import User, City


class CurrentUserHandler(MethodView):
    __base_uri__ = '/current_user/'
    __resource_name__ = 'current_user'

    @login_required()
    def get(self):
        user = User.load_current_user()
        return UserByIDHandler._get(user)

    @login_required()
    def patch(self):
        user = User.load_current_user()
        return UserByIDHandler._patch(user)
