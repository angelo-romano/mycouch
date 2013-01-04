from datetime import datetime, timedelta
from flask import request
from flask.views import MethodView
from mycouch.api.auth import login_required
from mycouch.api.utils import jsonify, get_logged_user, build_error_dict
from mycouch.core.utils import datetime_from_json
from mycouch.models import Activity, City
from functools import wraps


def force_model_instance(fn):
    @wraps(fn)
    def fn2(self, elem, *args, **kwargs):
        if not isinstance(elem, self.__model__):
            elem = self.__model__.query.filter_by(id=elem).first()
        return fn(self, elem, *args, **kwargs)
    return fn2


class ActivityHandler(MethodView):
    __base_uri__ = '/activities'
    __resource_name__ = 'activities'

    def get(self):
        # TODO - TO BE IMPROVED
        return jsonify([o.serialized for o in Activity.query.all()])

    @classmethod
    def validate(cls, user):
        param_errors = []
        params = dict(
            title=request.json.get('title'),
            description=request.json.get('description'),
            scheduled_from=datetime_from_json(
                request.json.get('scheduled_from')),
            creator_id=user.id,
            location=request.json.get('location'),
            city_id=request.json.get('city_id'))

        missing_params = [k for k, v in params.iteritems()
                          if v in ['', None]]

        param_errors = [
            'Field "%s" not specified.' % k for k in missing_params]

        optional_params = dict(
            scheduled_until=datetime_from_json(
                request.json.get('scheduled_until')))

        params.update(optional_params)

        # city must exist
        if (params.get('city_id') and not
                City.query.filter_by(id=params['city_id']).first()):
            param_errors.append('Invalid "city_id" value.')

        # can't create activities less than one hour in advance
        datetime_max = datetime.now() + timedelta(hours=1)
        if (params.get('scheduled_from') and
                params['scheduled_from'] < datetime_max):
            param_errors.append('Invalid "scheduled_from" value.')
        if (params.get('scheduled_until') and
                params['scheduled_until'] < datetime_max):
            param_errors.append('Invalid "scheduled_until" value.')

        if param_errors:  # in case of errors
            return (False, build_error_dict(param_errors))

        return (True, params)

    @login_required()
    def post(self):
        logged_user = get_logged_user()
        success, params = self.validate(logged_user)

        if not success:
            return (jsonify(params), 400, [])

        activity = Activity(**params)
        activity.save(commit=True)
        activity.set_user_rsvp(logged_user, 'yes')
        return ActivityByIDHandler._get(activity)


class ActivityByIDHandler(MethodView):
    __base_uri__ = '/activities/<int:id>'
    __resource_name__ = 'activities_one'
    __model__ = Activity

    @classmethod
    @force_model_instance
    def _get(cls, activity):
        return jsonify(activity.serialized)

    @classmethod
    @force_model_instance
    def _patch(cls, activity):
        params = dict(
            title=request.json.get('title'),
            description=request.json.get('description'),
            scheduled_from=datetime_from_json(
                request.json.get('scheduled_from')),
            location_id=request.json.get('location_id'),
            scheduled_until=datetime_from_json(
                request.json.get('scheduled_until')))

        for (key, val) in params.iteritems():
            curval = getattr(activity, key, None)
            if curval != val:
                setattr(activity, key, val)

        activity.save(commit=True)
        return cls._get(activity)

    def get(self, id):
        return self._get(id)

    @login_required()
    def patch(self, id):
        return self._patch(id)
