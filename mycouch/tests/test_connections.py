import os
import os.path
import sys
import unittest

cur_dir = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.append(cur_dir)

from mycouch import app, db
from mycouch.core.serializers import json_loads
from mycouch.tests.fixtures import with_fixtures
from mycouch.tests.helpers import (
    DATABASE_CONFIG, prepare_database, auth_user, send_call)

class ConnectionTestCase(unittest.TestCase):

    def setUp(self):
        if not app.config['TESTING']:
            prepare_database()
            app.config['SQLALCHEMY_DATABASE_URI'] = (
                'postgresql+psycopg2://%(username)s:%(password)s@%(host)s:%(port)s/%(dbname)s' %
                DATABASE_CONFIG)
            app.config['TESTING'] = True
            db.init_app(app)
            db.create_all()
        self.app = app.test_client()

    @with_fixtures('city', 'user')
    def test_friendship(self):
        # AUTHENTICATION here
        logged_user = auth_user(self.app, 'angelo', 'ciao')
        self.assertIsNotNone(logged_user)
        token = logged_user.get('token')

        # message failure(s) here
        # 1. invalid status
        request = {
            'description': 'A friend',
            'user_id': 2,
            'friendship_level': 'invalid',
        }
        resp = send_call(self.app, 'post', '/connections/friendships',
                         request, token=token)
        self.assertEquals(resp.status[:3], '400')

        # 2. invalid user
        request = {
            'description': 'A friend',
            'user_id': 666666,
            'friendship_level': 'friend',
        }
        resp = send_call(self.app, 'post', '/connections/friendships',
                         request, token=token)
        self.assertEquals(resp.status[:3], '400')

        # 3. missing description
        request = {
            'description': '',
            'user_id': 2,
            'friendship_level': 'friend',
        }
        resp = send_call(self.app, 'post', '/connections/friendships',
                         request, token=token)
        self.assertEquals(resp.status[:3], '400')

        # SUCCESSFUL HERE
        request = {
            'description': 'A friend.',
            'user_id': 2,
            'friendship_level': 'friend',
        }
        resp = send_call(self.app, 'post', '/connections/friendships',
                         request, token=token)
        self.assertEquals(resp.status[:3], '200')

        # fetching all friendship requests
        resp = send_call(self.app, 'get', '/connections/friendships',
                         token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertTrue(isinstance(resp_data, list))
        self.assertEquals(len(resp_data), 1)
        this_one = resp_data[0]
        this_one_id = resp_data[0].get('id')
        self.assertTrue(this_one_id > 0)
        self.assertTrue(all(v == this_one[k] for k, v in request.iteritems()))

        # fetching this friendship request
        resp = send_call(self.app, 'get',
                         '/connections/friendships/%s' % this_one_id,
                         token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertTrue(isinstance(resp_data, dict))
        self.assertTrue(all(v == this_one[k] for k, v in resp_data.iteritems()))

        # trying to "approve" friendship status (can be done only by the other
        # counterpart)
        patch_request = {'type_status': 'accepted'}
        resp = send_call(self.app, 'patch',
                         '/connections/friendships/%s' % this_one_id,
                         patch_request,
                         token=token)
        self.assertEquals(resp.status[:3], '405')

        # fetching a non-existing friendship request (404 expected)
        resp = send_call(self.app, 'get',
                         '/connections/friendships/%s' % (this_one_id + 1000),
                         token=token)
        self.assertEquals(resp.status[:3], '404')

        # AUTHENTICATION for other user here
        logged_user = auth_user(self.app, 'delgog', 'ciao')
        self.assertIsNotNone(logged_user)
        token = logged_user.get('token')

        # fetching this friendship request
        resp = send_call(self.app, 'get',
                         '/connections/friendships/%s' % this_one_id,
                         token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertTrue(isinstance(resp_data, dict))
        self.assertTrue(all(v == this_one[k] for k, v in resp_data.iteritems()
                            if k != 'user_id'))
        self.assertEquals(resp_data.get('user_id'), 1)

        # trying to "approve" friendship status (can be done only by the other
        # counterpart)
        # 1. invalid type status
        patch_request = {'type_status': 'invalid'}
        resp = send_call(self.app, 'patch',
                         '/connections/friendships/%s' % this_one_id,
                         patch_request,
                         token=token)
        self.assertEquals(resp.status[:3], '400')
        # 2. valid type status - success
        patch_request = {'type_status': 'accepted'}
        resp = send_call(self.app, 'patch',
                         '/connections/friendships/%s' % this_one_id,
                         patch_request,
                         token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertEquals(resp_data.get('type_status'), 'accepted')

    @with_fixtures('city', 'user')
    def test_reference(self):
        # AUTHENTICATION here
        logged_user = auth_user(self.app, 'angelo', 'ciao')
        self.assertIsNotNone(logged_user)
        token = logged_user.get('token')

        # message failure(s) here
        # 1. invalid status
        request = {
            'text': 'A reference',
            'user_id': 2,
            'reference_type': 'invalid',
        }
        resp = send_call(self.app, 'post', '/connections/references',
                         request, token=token)
        self.assertEquals(resp.status[:3], '400')

        # 2. invalid user
        request = {
            'text': 'A reference',
            'user_id': 66666,
            'reference_type': 'positive',
        }
        resp = send_call(self.app, 'post', '/connections/references',
                         request, token=token)
        self.assertEquals(resp.status[:3], '400')

        # 3. missing description
        request = {
            'text': '',
            'user_id': 2,
            'reference_type': 'positive',
        }
        resp = send_call(self.app, 'post', '/connections/references',
                         request, token=token)
        self.assertEquals(resp.status[:3], '400')

        # SUCCESSFUL HERE
        request = {
            'text': 'A reference',
            'user_id': 2,
            'reference_type': 'positive',
        }
        resp = send_call(self.app, 'post', '/connections/references',
                         request, token=token)
        self.assertEquals(resp.status[:3], '200')

        # fetching all friendship requests
        resp = send_call(self.app, 'get', '/connections/references',
                         token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertTrue(isinstance(resp_data, list))
        self.assertEquals(len(resp_data), 1)
        this_one = resp_data[0]
        this_one_id = this_one.get('id')
        self.assertTrue(this_one_id > 0)
        self.assertTrue(all(v == this_one[k] for k, v in request.iteritems()))

        # fetching this friendship request
        resp = send_call(self.app, 'get',
                         '/connections/references/%s' % this_one_id,
                         token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertTrue(isinstance(resp_data, dict))
        self.assertTrue(all(v == this_one[k] for k, v in resp_data.iteritems()))

        # fetching a non-existing friendship request (404 expected)
        resp = send_call(self.app, 'get',
                         '/connections/references/%s' % (this_one_id + 1000),
                         token=token)
        self.assertEquals(resp.status[:3], '404')

        # AUTHENTICATION for other user here
        logged_user = auth_user(self.app, 'delgog', 'ciao')
        self.assertIsNotNone(logged_user)
        token = logged_user.get('token')

        # fetching this friendship request
        resp = send_call(self.app, 'get',
                         '/connections/references/%s' % this_one_id,
                         token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertTrue(isinstance(resp_data, dict))
        self.assertTrue(all(v == this_one[k] for k, v in resp_data.iteritems()
                            if k != 'user_id'))
        self.assertEquals(resp_data.get('user_id'), 1)


    def tearDown(self):
        db.session.close()

if __name__ == '__main__':
    unittest.main()
