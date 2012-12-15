from flask import request, redirect, url_for, jsonify, make_response
from flask.views import MethodView
from flaskext.auth import login_required, logout, get_current_user_data
from flaskext.auth.models.sa import get_user_class
from geoalchemy import WKTSpatialElement
from mycouch import app, db
from mycouch.models import User, City


class AuthHandler(MethodView):
    __base_uri__ = '/auth/'
    __resource_name__ = 'auth'

    def get(self):
        username, password = (
            request.args.get('username'), request.args.get('password'))
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify(success=False)
        if user.authenticate(password):
            return jsonify(success=True)
        return jsonify(success=False)


class UserHandler(MethodView):
    __base_uri__ = '/users/'
    __resource_name__ = 'user'

    @login_required()
    def get(self):
        user = User.load_current_user()
        return jsonify(user.serialized)

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


class CityHandler(MethodView):
    __base_uri__ = '/cities/'
    __resource_name__ = 'cities'

    def get(self):
        return (401, 'NOT IMPLEMENTED', {})

    def post(self):
        params = dict(
            name=request.json.get('name'),
            country_code=request.json.get('country_code'),
            latitude=request.json.get('latitude'),
            longitude=request.json.get('longitude'))

        optional_params=dict(
            rating=request.json.get('rating'),
            timezone=request.json.get('timezone'),
            slug=request.json.get('slug'),
            wikiname=request.json.get('wikiname'))

        if not all(params.values()):
            return (jsonify(error=True), 300, [])

        params.update(optional_params)

        params['coordinates'] = WKTSpatialElement(
            'POINT(%s %s)' % (
                params.get('latitude'),
                params.get('longitude')))
        del params['latitude']
        del params['longitude']

        city = City(**params)
        city.save(commit=True)
        return jsonify(city.serialized)


class CityHandlerByID(MethodView):
    __base_uri__ = '/cities/<int:pk>/'
    __resource_name__ = 'city'

    def get(self, pk):
        city = City.query.filter_by(id=pk).first()

        if not city:
            return (404, 'NOT FOUND', [])

        return jsonify(city.serialized)
