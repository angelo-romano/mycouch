from flask import request
from flask.views import MethodView
from geoalchemy import WKTSpatialElement
from mycouch.api.auth import login_required
from mycouch.api.utils import jsonify, get_logged_user, get_filter_dict
from mycouch.models import City, MinorLocality, Group, GroupPost
from sqlalchemy import func


class GroupHandler(MethodView):
    __base_uri__ = '/groups'
    __resource_name__ = 'groups'

    def get(self):
        # TODO - search to be defined
        filter_args = get_filter_dict(
            request.args, ('city_id', 'parent_group_id'))
        query = Group.query.filter_by(is_active=True)
        if filter_args:
            query = query.filter_by(**filter_args)
        resp = [o.serialized for o in query]
        return jsonify(resp)

    @login_required()
    def post(self):
        """
        Create new group.

        {
            "title": str,
            "description": str,
            ^"city_id": int,
            ^"minorlocality_id": int,
            ^"parent_group_id": int}
        """
        user = get_logged_user()
        params = dict(
            title=request.json.get('title'),
            creator_id=user.id)

        optional_params = dict(
            description=request.json.get('description'),
            city_id=request.json.get('city_id'),
            minorlocality_id=request.json.get('minorlocality_id'),
            parent_group_id=request.json.get('parent_group_id'))

        if not all([v not in (None, '') for v in params.itervalues()]):
            return (jsonify(error=True), 400, [])

        if (optional_params['city_id'] is None and
                optional_params['minorlocality_id'] is not None):
            return (jsonify(error=True), 400, [])

        if (optional_params['parent_group_id'] is not None):
            parent_group = Group.query.filter_by(
                id=optional_params['parent_group_id']).first()
            if not parent_group:
                return (jsonify(error=True), 400, [])
            elif parent_group.city_id != optional_params['city_id']:
                return (jsonify(error=True), 400, [])

        params.update(optional_params)

        group = Group(**params)
        group.save(commit=True)
        return GroupByIDHandler._get(group)


class GroupByIDHandler(MethodView):
    __base_uri__ = '/groups/<int:id>'
    __resource_name__ = 'groups_one'

    @classmethod
    def _get(cls, group):
        resp = group.serialized
        return jsonify(resp)

    def get(self, id):
        group = Group.query.filter_by(id=id).first()

        if not group:
            return ('NOT FOUND', 404, [])

        return self._get(group)
