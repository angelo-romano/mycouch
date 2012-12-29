import os
import os.path
import simplejson
import sys
import unittest
from datetime import date

cur_dir = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.append(cur_dir)

from mycouch import app, db
from mycouch.core.serializers import json_loads
from mycouch.tests.helpers import (
    DATABASE_CONFIG, prepare_database, send_call, auth_user)


class MyCouchTestCase(unittest.TestCase):

    def setUp(self):
        prepare_database()
        app.config['SQLALCHEMY_DATABASE_URI'] = (
            'postgresql+psycopg2://%(username)s:%(password)s@%(host)s:%(port)s/%(dbname)s' %
            DATABASE_CONFIG)
        app.config['TESTING'] = True
        db.init_app(app)
        db.create_all()
        self.app = app.test_client()

    def test_this(self):
        today = date.today()
        data = {
            'username': 'angelo',
            'password': 'ciao',
            'first_name': 'Angelo',
            'last_name': 'Romano',
            'email': 'angelo.romano@gmail.com',
            'gender': '1',
            'birth_date': date(today.year - 21, today.month, today.day),
        }
        data2 = {
            'username': 'angelo1',
            'password': 'ciao1',
            'first_name': 'Angelo1',
            'last_name': 'Romano1',
            'email': 'angelo.romano1@gmail.com',
            'gender': '1',
            'birth_date': date(today.year - 31, today.month, today.day),
        }
        # CREATING ACCOUNT 1
        resp = send_call(self.app, 'post', '/users', data)
        resp_data = json_loads(resp.data)
        self.assertTrue(all(data.get(key) == resp_data.get(key)
                            for key in data.iterkeys()
                            if key != 'password'))
        id_one = resp_data['id']
        self.assertTrue(id_one > 0)
        # CREATING ACCOUNT 2
        resp = send_call(self.app, 'post', '/users', data2)
        resp_data2 = json_loads(resp.data)
        self.assertTrue(all(data2[key] == resp_data2[key]
                            for key in data.iterkeys()
                            if key != 'password'))
        id_two = resp_data2['id']
        self.assertTrue(id_two > 0)
        # GET EXPLICIT USER - AUTH FAILURE
        resp = send_call(self.app, 'get', '/current_user')
        self.assertEquals(resp.status[:3], '401')
        # AUTHENTICATION COMES HERE
        resp = auth_user(self.app, data['username'], data['password'] + 'no')
        self.assertIsNone(resp)

        resp = auth_user(self.app, data['username'], data['password'])
        self.assertIsNotNone(resp)
        token = resp.get('token')

        # GET EXPLICIT CURRENT USER - NOW WORKS
        resp = send_call(self.app, 'get', '/current_user', token=token)
        resp_data = json_loads(resp.data)
        self.assertEquals(resp.status[:3], '200')
        self.assertEquals(resp_data.get('id'), id_one)

        # GET EXPLICIT USERS
        resp = send_call(self.app, 'get', '/users/%s' % id_one, token=token)
        resp_data = json_loads(resp.data)
        self.assertEquals(resp.status[:3], '200')
        self.assertTrue(all(data[key] == resp_data[key]
                            for key in data.iterkeys()
                            if key != 'password'))
        resp = send_call(self.app, 'get', '/users/%s' % id_two, token=token)
        resp_data = json_loads(resp.data)
        self.assertEquals(resp.status[:3], '200')
        self.assertTrue(all(data2[key] == resp_data[key]
                            for key in data.iterkeys()
                            if key != 'password'))

        # UPDATE USER
        patch_data = {
            'details': {
                'websites': ['http://www.angeloromano.com'],
                'sections': {
                    'summary': 'This is a summary.',
                    'couch_info': 'This is my couch info.',
                },
                'profile_details': {
                    'occupation': 'My occupation.',
                },
            },
        }
        resp = send_call(self.app, 'patch', '/current_user',
                         patch_data, token=token)
        resp_data = json_loads(resp.data)
        self.assertEquals(resp.status[:3], '200')
        self.assertTrue(all(data[key] == resp_data[key]
                            for key in data.iterkeys()
                            if key != 'password'))
        self.assertEquals(resp_data.get('details'), patch_data['details'])

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
