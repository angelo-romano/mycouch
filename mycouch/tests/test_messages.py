import os
import os.path
import sys
import unittest

cur_dir = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.append(cur_dir)

from mycouch import app, db
from mycouch.core.serializers import json_loads
from mycouch.tests.fixtures import with_base_fixtures
from mycouch.tests.helpers import (
    DATABASE_CONFIG, prepare_database, auth_user, send_call)


class LocationTestCase(unittest.TestCase):

    def setUp(self):
        prepare_database()
        app.config['SQLALCHEMY_DATABASE_URI'] = (
            'postgresql+psycopg2://%(username)s:%(password)s@%(host)s:%(port)s/%(dbname)s' %
            DATABASE_CONFIG)
        app.config['TESTING'] = True
        db.init_app(app)
        db.create_all()
        self.app = app.test_client()

    def _sender_login(self):
        # AUTHENTICATION here
        logged_user = auth_user(self.app, 'angelo', 'ciao')
        self.assertIsNotNone(logged_user)
        token = logged_user.get('token')

        return token, logged_user

    def _recipient_login(self):
        # AUTHENTICATION here
        logged_user = auth_user(self.app, 'delgog', 'ciao')
        self.assertIsNotNone(logged_user)
        token = logged_user.get('token')

        return token, logged_user

    @with_base_fixtures
    def test_this(self):
        request = {
            'subject': 'A Test Message',
            'text': 'A test text...',
            'recipient_list_ids': [2],
        }
        token, logged_user = self._sender_login()

        # message failure here
        resp = send_call(self.app, 'post', '/messages/in/privates',
                         request, token=token)
        self.assertEquals(resp.status[:3], '403')
        # message being sent here
        resp = send_call(self.app, 'post', '/messages/out/privates',
                         request, token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        msg_id = resp_data.get('id')
        self.assertEquals(logged_user.get('id'), resp_data.get('sender_id'))
        self.assertIsNotNone(msg_id)
        # message retrieval
        resp = send_call(self.app, 'get', '/messages/out/privates',
                         request, token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertTrue(isinstance(resp_data, list) and len(resp_data) == 1)
        resp_data = resp_data[0]
        self.assertTrue(all(
            v == resp_data.get(k)
            for (k, v) in request.iteritems()))
        self.assertEquals(logged_user.get('id'), resp_data.get('sender_id'))
        # message retrieval (explicit ID)
        resp = send_call(self.app, 'get',
                         '/messages/out/privates/%s' % msg_id,
                         request, token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertTrue(isinstance(resp_data, dict))
        self.assertTrue(all(
            v == resp_data.get(k)
            for (k, v) in request.iteritems()))
        self.assertEquals(logged_user.get('id'),
                          resp_data.get('sender_id'))
        # changing message status is allowed only for the recipients
        resp = send_call(self.app, 'patch',
                         '/messages/out/privates/%s' % msg_id,
                         {'message_status': 'read'}, token=token)
        self.assertEquals(resp.status[:3], '403')
        # ensures the other user has successfully received the message
        # -- 1. authentication
        sender_user_id = logged_user.get('id')
        token, logged_user = self._recipient_login()
        # -- 2. retrieval
        resp = send_call(self.app, 'get',
                         '/messages/in/privates',
                         request, token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertTrue(isinstance(resp_data, list) and len(resp_data) == 1)
        resp_data = resp_data[0]
        self.assertTrue(all(
            v == resp_data.get(k)
            for (k, v) in request.iteritems()))
        self.assertEquals(sender_user_id, resp_data.get('sender_id'))
        self.assertEquals(resp_data.get('message_status'), 'unread')
        msg_id = resp_data.get('id')
        # changing message status is not allowed here - token must be passed
        resp = send_call(self.app, 'patch',
                         '/messages/in/privates/%s' % msg_id,
                         {'message_status': 'read'})
        self.assertEquals(resp.status[:3], '401')
        # changing message status is allowed here
        resp = send_call(self.app, 'patch',
                         '/messages/in/privates/%s' % msg_id,
                         {'message_status': 'read'}, token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertEquals(resp_data.get('message_status'), 'read')
        # changing message status is not allowed here - wrong value
        resp = send_call(self.app, 'patch',
                         '/messages/in/privates/%s' % msg_id,
                         {'message_status': 'misread'}, token=token)
        self.assertEquals(resp.status[:3], '400')

        # writes a reply
        request = {
            'subject': 'A Test Message',
            'text': 'A test text...',
            'recipient_list_ids': [1],
            'reply_to_id': msg_id,
        }
        resp = send_call(self.app, 'post', '/messages/out/privates',
                         request, token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        msg_id = resp_data.get('id')
        self.assertEquals(logged_user.get('id'), resp_data.get('sender_id'))
        self.assertTrue(all(
            v == resp_data.get(k)
            for (k, v) in request.iteritems()))

        # time to read the reply
        token, logged_user = self._sender_login()
        resp = send_call(self.app, 'get',
                         '/messages/in/privates/%s' % msg_id)
        # no token - 401
        self.assertEquals(resp.status[:3], '401')
        # token specified - 200
        resp = send_call(self.app, 'get',
                         '/messages/in/privates/%s' % msg_id,
                         token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertTrue(all(
            v == resp_data.get(k)
            for (k, v) in request.iteritems()))
        self.assertEquals(resp_data.get('message_status'), 'unread')

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
