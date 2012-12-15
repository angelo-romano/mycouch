from flask import request, redirect, url_for, jsonify, make_response
from flask.views import MethodView
from flaskext.auth import login_required, logout, get_current_user_data
from flaskext.auth.models.sa import get_user_class
from geoalchemy import WKTSpatialElement
from mycouch import app, db
from mycouch.models import User, City


LOCATION_TYPE_MAPPING = {
    'city': City,
}


class LocationHandler(MethodView):
    __base_uri__ = '/locations/<loctype>'
    __resource_name__ = 'locations'

    def post(self, loctype):
        if loctype not in LOCATION_TYPE_MAPPING:
            return ('TYPE', '400', [])
        location_class = LOCATION_TYPE_MAPPING[loctype]

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

        location = location_class(**params)
        location.save(commit=True)
        resp = location.serialized
        resp['type'] = loctype
        return jsonify(resp)


class LocationByIDHandler(MethodView):
    __base_uri__ = '/locations/<loctype>/<int:id>'
    __resource_name__ = 'locations_one'

    def get(self, loctype, id):
        if loctype not in LOCATION_TYPE_MAPPING:
            return ('TYPE', '400', [])
        location_class = LOCATION_TYPE_MAPPING[loctype]
        location = location_class.query.filter_by(id=id).first()

        if not location:
            return ('NOT FOUND', 404, [])

        resp = location.serialized
        resp['type'] = loctype
        return jsonify(resp)
