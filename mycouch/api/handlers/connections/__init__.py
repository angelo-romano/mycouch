from flask import request
from flask.views import MethodView
from flaskext.auth import login_required
from geoalchemy import WKTSpatialElement
from mycouch.api.utils import jsonify, get_logged_user
from mycouch.models import City, Reference, FriendshipConnection
from sqlalchemy import or_


CONNECTION_TYPE_MAPPING = {
    'friendships': {  # URL type is key
        'validator': 'validate_friendship',
        'type': 'friendship',
        'class': FriendshipConnection},
    'references': {
        'validator': 'validate_reference',
        'type': 'reference',
        'class': Reference},
}


class ConnectionHandler(MethodView):
    __base_uri__ = '/connections/<conntype>'
    __resource_name__ = 'connections'

    @staticmethod
    def validate_friendship(user):
        """
        Expected form:

            {"description": str, "other_user_id": int,
             "friendship_level"}
        """
        params = dict(
            description=request.json.get('description'),
            user_from_id=user.id,
            user_to_id=request.json.get('other_user_id'),
            type_status='pending',
            flags=filter(None,
                [request.json.get('friendship_level', 'friend')]))
        return params

    @staticmethod
    def validate_reference(user):
        """
        Expected form:

            {"text": str, "other_user_id": int, "type": str}
        """
        params = dict(
            text=request.json.get('text'),
            user_from_id=user.id,
            user_to_id=request.json.get('other_user_id'),
            type_status=request.json.get('type'))
        return (params, optional_params)

    #login_required()
    def get(self, conntype):
        print 'a1'
        user = get_logged_user()
        if conntype not in CONNECTION_TYPE_MAPPING:
            return ('TYPE', '400', [])
        conn_dict = CONNECTION_TYPE_MAPPING[conntype]

        conn_class = conn_dict['class']

        conn_list = conn_class.query.filter(or_(
            conn_class.user_from_id == user.id,
            conn_class.user_to_id == user.id)).all()
        resp = [conn.serialized_func(user) for conn in conn_list]
        return jsonify(resp)

    @login_required()
    def post(self, conntype):
        logged_user = get_logged_user()
        if conntype not in CONNECTION_TYPE_MAPPING:
            return ('TYPE', '400', [])
        conn_dict = CONNECTION_TYPE_MAPPING[conntype]

        conn_class, conn_validator = (
            conn_dict['class'],
            getattr(self, conn_dict['validator']))

        success, param_dict = getattr(
            self, conn_dict['validator'])(logged_user)
        if not success:
            return param_dict

        conn = conn_class(**param_dict)
        conn.save(commit=True)
        return jsonify(conn.serialized_func(user))


class ConnectionByIDHandler(MethodView):
    __base_uri__ = '/connections/<conntype>/<int:id>'
    __resource_name__ = 'connections_one'

    def get(self, conntype, id):
        logged_user = get_logged_user()
        if conntype not in CONNECTION_TYPE_MAPPING:
            return ('TYPE', '400', [])
        conn_dict = CONNECTION_TYPE_MAPPING[conntype]

        conn_class, conn_serializer = (
            conn_dict['class'],
            getattr(self, conn_dict['serializer']))

        conn_list = conn_class.query.filter(or_(
            conn_class.user_from_id == id,
            conn_class.user_to_id == id)).all()
        resp = [conn.serialized_func(user) for conn in conn_list]
        return jsonify(resp)


