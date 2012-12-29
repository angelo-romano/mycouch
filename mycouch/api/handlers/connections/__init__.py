from flask import request
from flask.views import MethodView
from mycouch.api.auth import login_required
from mycouch.api.utils import (
    jsonify, get_logged_user, build_error_dict, model_by_id)
from mycouch.models import Reference, FriendshipConnection, User
from mycouch.core.db.types import (
    StateValueError, StateTransitionError, make_transition)
from sqlalchemy import or_, and_


CONNECTION_TYPE_MAPPING = {
    'friendships': {  # URL type is key
        'validator': 'validate_friendship',
        'type': 'friendship',
        'mandatory_params': ('description', 'user_id', 'friendship_level'),
        'class': FriendshipConnection},
    'references': {
        'validator': 'validate_reference',
        'type': 'reference',
        'mandatory_params': ('text', 'user_id', 'reference_type'),
        'class': Reference},
}


class ConnectionHandler(MethodView):
    __base_uri__ = '/connections/<conntype>'
    __resource_name__ = 'connections'

    @classmethod
    def _validate_params(cls, conntype, user):
        """
        """
        mandatory_params = (
            CONNECTION_TYPE_MAPPING[conntype]['mandatory_params'])

        # checking for mandatory parameters
        missing_mandatory_params = (
            [k for k in mandatory_params
             if request.json.get(k) in (None, '')])
        if missing_mandatory_params:
            return (False, build_error_dict([
                'Field "%s" not specified.' % field
                for field in missing_mandatory_params]))

        # validate user id value
        if not (User.query.filter(and_(
                User.is_active,
                User.id != user.id,
                User.id == request.json.get('user_id'))).first()):
            return (False, build_error_dict([
                'Invalid "user_id" value.']))

        # preparing param dict
        params = dict(
            description=request.json.get('description'),
            text=request.json.get('text'),
            user_from_id=user.id,
            user_to_id=request.json.get('user_id'))

        return (True, params)

    @classmethod
    def validate_friendship(cls, user):
        """
        Expected form:

            {"description": str, "other_user_id": int,
             "friendship_level"}
        """
        success, params = cls._validate_params('friendships', user)

        if not success:
            return (success, params)

        # validate friendship level value
        if not FriendshipConnection.validate_friendship_level(
                request.json.get('friendship_level')):
            return (False, build_error_dict(
                ['Invalid "friendship_level" value.']))

        # preparing param dict
        params.update(dict(
            text=request.json.get('description'),
            type_status='pending',
            flags=filter(None,
                         [request.json.get('friendship_level', 'friend')])))

        return (True, params)

    @classmethod
    def validate_reference(cls, user):
        """
        Expected form:

            {"description": str, "other_user_id": int,
             "friendship_level"}
        """
        success, params = cls._validate_params('references', user)

        if not success:
            return (success, params)

        # validate friendship level value
        if not Reference.validate_reference_type(
                request.json.get('reference_type')):
            return (False, build_error_dict(
                ['Invalid "reference_type" value.']))

        # preparing param dict
        params.update(dict(
            description='reference',
            type_status=request.json.get('reference_type'),
            flags=filter(None,
                         [request.json.get('reference_type')])))

        return (True, params)

    @login_required()
    def get(self, conntype):
        user = get_logged_user()
        if conntype not in CONNECTION_TYPE_MAPPING:
            return ('TYPE', '400', [])
        conn_dict = CONNECTION_TYPE_MAPPING[conntype]

        conn_class = conn_dict['class']

        conn_list = conn_class.query.filter(or_(
            conn_class.user_from_id == user.id,
            conn_class.user_to_id == user.id)).all()
        resp = [conn.serializer_func(user) for conn in conn_list]
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
            return (jsonify(**param_dict), 400, [])
        conn = conn_class(**param_dict)
        conn.save(commit=True)
        return jsonify(conn.serializer_func(logged_user))


class ConnectionByIDHandler(MethodView):
    __base_uri__ = '/connections/<conntype>/<int:id>'
    __resource_name__ = 'connections_one'

    @classmethod
    @model_by_id(Reference)
    def _reference_get(cls, conn):
        return cls._get('references', conn)

    @classmethod
    @model_by_id(FriendshipConnection)
    def _friendship_get(cls, conn):
        return cls._get('friendships', conn)

    @classmethod
    def _get(cls, conntype, conn):
        logged_user = get_logged_user()
        if not conn:
            return ('NOT FOUND', 404, [])

        this_conn = cls._get_instance(conntype, conn)
        if isinstance(this_conn, tuple):
            return this_conn

        return jsonify(this_conn.serializer_func(logged_user))

    @classmethod
    def _get_instance(cls, conntype, conn_or_id):
        logged_user = get_logged_user()
        conn_dict = CONNECTION_TYPE_MAPPING[conntype]
        conn_class = conn_dict['class']

        if isinstance(conn_or_id, conn_class):
            conn = conn_or_id
        else:
            conn = conn_class.query.filter_by(id=conn_or_id).first()
            if not conn:
                return ('NOT FOUND', 404, [])

        conn = conn_class.query.filter(or_(
            conn_class.user_from_id == logged_user.id,
            conn_class.user_to_id == logged_user.id)).filter(
                conn_class.id == conn.id).first()

        if not conn:
            return ('UNAUTHORIZED', 405, [])

        return conn

    @login_required()
    def get(self, conntype, id):
        if conntype not in CONNECTION_TYPE_MAPPING:
            return ('TYPE', 400, [])
        if conntype == 'friendships':
            return self._friendship_get(id)
        elif conntype == 'references':
            return self._reference_get(id)

    @login_required()
    def patch(self, conntype, id):
        if conntype not in CONNECTION_TYPE_MAPPING:
            return ('TYPE', 400, [])
        conn_dict = CONNECTION_TYPE_MAPPING[conntype]
        conn_class = conn_dict['class']

        conn = self._get_instance(conntype, id)
        if not isinstance(conn, conn_class):
            # error
            return conn

        logged_user = get_logged_user()

        if conntype == 'friendships':
            type_status = request.json.get('type_status')
            if type_status:
                # pending status can be changed only by the other counterpart
                # (to be improved yet)
                if (conn.type_status['current'] == 'pending' and
                        conn.user_from_id == logged_user.id):
                    return ('UNAUTHORIZED', 405, [])
                try:
                    make_transition(conn, 'type_status', type_status)
                except StateValueError:
                    return (jsonify(build_error_dict([
                        'Invalid "type_status" value.'])), 400, [])
                except StateTransitionError:
                    return (jsonify(build_error_dict([
                        'Invalid "type_status" transition.'])), 400, [])

        return jsonify(conn.serializer_func(logged_user))
