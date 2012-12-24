from flask import request
from flask.views import MethodView
from mycouch.api.utils import jsonify, get_logged_user, login_required
from mycouch.core.utils import datetime_from_json
from mycouch.models import Activity
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

    @login_required()
    def post(self):
        logged_user = get_logged_user()
        params = dict(
            title=request.json.get('title'),
            description=request.json.get('description'),
            scheduled_from=datetime_from_json(
                request.json.get('scheduled_from')),
            creator_id=logged_user.id,
            location=request.json.get('location'),
            locality_id=request.json.get('locality_id'))

        optional_params = dict(
            scheduled_until=datetime_from_json(
                request.json.get('scheduled_until')))

        if not all(params.values()):
            missing_fields = [k for k, v in params.iteritems()
                              if not v]
            return (jsonify(error=True, missing=missing_fields), 400, [])

        params.update(optional_params)

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
