from flask import request
from flask.views import MethodView
from mycouch.api.auth import login_required
from mycouch.api.utils import jsonify, get_logged_user, build_error_dict
from mycouch.models import (
    User,
    PrivateMessage, PrivateMessageNotification,
    HospitalityRequest, HospitalityRequestNotification)
from sqlalchemy import and_


MESSAGE_TYPE_MAPPING = {
    'privates': {  # URL type is key
        'validator': 'validate_private_message',
        'type': 'private',
        'class': PrivateMessage,
        'notification_class': PrivateMessageNotification,
    },
    'hospitality_requests': {
        'validator': 'validate_hospitality_request',
        'type': 'hospitality_request',
        'class': HospitalityRequest,
        'notification_class': HospitalityRequestNotification,
    },
}


def filter_by_direction(msgtype, direction, user, additional_filters=None):
    """
    Builds a query for direction filtering purposes.
    """
    base_class = MESSAGE_TYPE_MAPPING[msgtype]['class']
    if direction == 'in':
        resp = base_class.get_incoming(
            user, additional_filters=additional_filters)
    elif direction == 'out':
        resp = base_class.get_outgoing(
            user, additional_filters=additional_filters)
    else:
        raise ValueError('Invalid "direction" value.')

    return resp


class MessageHandler(MethodView):
    __base_uri__ = '/messages/<direction>/<msgtype>'
    __resource_name__ = 'messages'

    @staticmethod
    def _validate_message(cls, user):
        """
        Expected form:

            {"subject": str, "text": str, "recipient_list_ids": [int*]}
        """
        # recipient list validation
        recipient_list_objects = User.query.filter(and_(
            User.id.in_(request.json.get('recipient_list_ids')),
            User.id != user.id,
            User.is_active)).all()
        recipient_list_ids = [o.id for o in recipient_list_objects]
        # param dict built here
        params = dict(
            subject=request.json.get('subject'),
            sender_id=user.id,
            text=request.json.get('text'),
            recipient_list_ids=recipient_list_ids)
        optional_params = dict(
            message_status=request.json.get('message_status'),
            reply_to_id=request.json.get('reply_to_id'))

        # checking for mandatory parameters
        missing_mandatory_params = (
            [k for (k, v) in params.iteritems() if not v])
        if missing_mandatory_params:
            return (False, build_error_dict([
                'Field "%s" not specified' % field
                for field in missing_mandatory_params]))

        # checking for additional param validity
        if optional_params['reply_to_id']:
            parent_msg = cls.query.filter_by(
                id=optional_params['reply_to_id']).first()

            if not parent_msg:
                # cannot reply to the original message - not found
                return (False,
                        build_error_dict(['Original message not found.']))
            elif user.id not in parent_msg.recipient_list_ids:
                # user not in the destination list
                return (False,
                        build_error_dict(['Cannot reply to this message.']))

        # preparing the full param dict to be returned
        for (k, v) in optional_params.iteritems():
            if v is not None:
                params[k] = v

        # success!
        return (True, params)

    @classmethod
    def validate_private_message(cls, user):
        success, params = cls._validate_message(PrivateMessage, user)
        # TODO - status validation
        return (success, params)

    @classmethod
    def validate_hospitality_request(cls, user):
        success, params = cls._validate_message(PrivateMessage, user)
        # TODO - status validation
        if success:
            recipient_list_ids = params.get('recipient_list_ids')
            if len(recipient_list_ids) != 1:
                return (False,
                        build_error_dict(['Must be exactly one recipient!']))
        return (success, params)

    @login_required()
    def get(self, direction, msgtype):
        user = get_logged_user()
        if msgtype not in MESSAGE_TYPE_MAPPING:
            return ('TYPE', 400, [])

        try:
            msg_list = filter_by_direction(msgtype, direction, user)
        except ValueError:
            return ('DIRECTION', 400, [])

        resp = [msg.serialized_func(user) for msg in msg_list]
        return jsonify(resp)

    @login_required()
    def post(self, direction, msgtype):
        user = get_logged_user()
        if direction != 'out':
            return ('NOT ALLOWED', 403, [])

        logged_user = get_logged_user()
        if msgtype not in MESSAGE_TYPE_MAPPING:
            return ('TYPE', 400, [])
        msg_dict = MESSAGE_TYPE_MAPPING[msgtype]

        msg_class, msg_validator = (
            msg_dict['class'],
            getattr(self, msg_dict['validator']))

        success, param_dict = getattr(
            self, msg_dict['validator'])(logged_user)
        if not success:
            return (jsonify(param_dict), 400, [])

        msg = msg_class(**param_dict)
        msg.send_to(*msg.recipient_list)
        return jsonify(msg.serialized_func(user))


class MessageByIDHandler(MethodView):
    __base_uri__ = '/messages/<direction>/<msgtype>/<int:id>'
    __resource_name__ = 'messages_one'

    @login_required()
    def get(self, direction, msgtype, id):
        user = get_logged_user()
        if msgtype not in MESSAGE_TYPE_MAPPING:
            return ('TYPE', 400, [])
        try:
            msg_list = filter_by_direction(
                msgtype, direction, user, additional_filters={'id': id})
        except ValueError:
            return ('DIRECTION', 400, [])
        if not msg_list:
            return ('NOT FOUND', 404, [])
        msg = msg_list[0]

        return jsonify(msg.serialized_func(user))

    @login_required()
    def patch(self, direction, msgtype, id):
        user = get_logged_user()
        if msgtype not in MESSAGE_TYPE_MAPPING:
            return ('TYPE', 400, [])
        msg_dict = MESSAGE_TYPE_MAPPING[msgtype]
        msg_notification_class = msg_dict['notification_class']

        if direction == 'out':  # PATCH op is allowed only for incoming msgs
            return ('FORBIDDEN', 403, [])
        elif direction != 'in':  # Invalid direction value
            return ('DIRECTION', 400, [])

        msg_list = filter_by_direction(
            msgtype, 'in', user, additional_filters={'id': id})
        if not msg_list:
            return ('NOT FOUND', 404, [])

        msg = msg_list[0]

        added_flags, removed_flags = (
            request.json.get('flags_in'),
            request.json.get('flags_out'))

        msg.change_flags(added_flags, removed_flags)

        msg_notification = msg.get_notification(user)
        errors = []

        try:
            msg_notification.change_status(request.json.get('message_status'))
        except ValueError:  # Invalid transition
            errors.append('Invalid "message_status" value.')

        if msgtype == 'hospitality_request':
            request_status = request.json.get('request_status')
            if (request_status and
                ((direction == 'out' and request_status == 'canceled')
                 or direction == 'in' and msg.status != 'canceled')):
                try:
                    msg.change_status(request_status)
                except ValueError:  # Invalid transition
                    errors.append('Invalid "request_status" value.')

        if errors:  # Errors found, returns error structure
            return (jsonify(build_error_dict(errors)), 400, [])

        # in case of success, returns the updated message serialization
        msg.save()
        msg_notification.save(commit=True)
        return jsonify(msg.serialized_func(user))
