from flask import request
from flask.views import MethodView
from geoalchemy import WKTSpatialElement
from mycouch.api.auth import login_required
from mycouch.api.utils import jsonify, get_logged_user, build_error_dict
from mycouch.models import City, MinorLocality
from sqlalchemy import func


LOCATION_TYPE_MAPPING = {
    'cities': City,
    'minor_locations': MinorLocality,
}


class LocationHandler(MethodView):
    __base_uri__ = '/locations/<loctype>'
    __resource_name__ = 'locations'

    def get(self, loctype):
        logged_user = get_logged_user()
        if loctype not in LOCATION_TYPE_MAPPING:
            return ('TYPE', '400', [])
        location_class = LOCATION_TYPE_MAPPING[loctype]
        loc_query = location_class.query
        if logged_user:
            make_point = lambda c: func.ST_SetSRID(
                func.ST_Point(c.x, c.y), 4326)
            loc_query = loc_query.filter(
                func.ST_Distance_Sphere(
                    make_point(location_class.coordinates),
                    make_point(logged_user.city.coordinates)) < 100000)
        loc_query = loc_query.order_by('-rating').limit(10)
        resp = [o.serialized for o in loc_query]
        return jsonify(resp)

    @login_required()
    def post(self, loctype):
        if loctype not in LOCATION_TYPE_MAPPING:
            return ('TYPE', '400', [])
        location_class = LOCATION_TYPE_MAPPING[loctype]

        params = dict(
            name=request.json.get('name'),
            country_id=request.json.get('country_id'),
            latitude=request.json.get('latitude'),
            longitude=request.json.get('longitude'))

        optional_params = dict(
            rating=request.json.get('rating'),
            timezone=request.json.get('timezone'),
            slug=request.json.get('slug'),
            wikiname=request.json.get('wikiname'))

        missing_vals = [(k, v) for (k, v) in params.iteritems()
                        if v in (None, '')]
        if missing_vals:
            error_dict = build_error_dict([
                '"%s" not specified' % k for (k, _) in missing_vals])
            return (jsonify(error_dict), 400, [])

        params.update(optional_params)

        params['coordinates'] = WKTSpatialElement(
            'POINT(%s %s)' % (
                params.get('latitude'),
                params.get('longitude')))
        del params['latitude']
        del params['longitude']

        location = location_class(**params)
        location.save(commit=True)
        return LocationByIDHandler._get(loctype, location)


class LocationByIDHandler(MethodView):
    __base_uri__ = '/locations/<loctype>/<int:id>'
    __resource_name__ = 'locations_one'

    @classmethod
    def _get(cls, loctype, location):
        resp = location.serialized
        resp['type'] = loctype
        return jsonify(resp)

    def get(self, loctype, id):
        if loctype not in LOCATION_TYPE_MAPPING:
            return ('TYPE', '400', [])
        location_class = LOCATION_TYPE_MAPPING[loctype]
        location = location_class.query.filter_by(id=id).first()

        if not location:
            return ('NOT FOUND', 404, [])

        return self._get(loctype, location)
