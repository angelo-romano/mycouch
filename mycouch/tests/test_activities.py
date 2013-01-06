import os
import os.path
import sys
import unittest
from datetime import datetime, timedelta

cur_dir = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.append(cur_dir)

from mycouch import app, db
from mycouch.core.serializers import json_loads
from mycouch.tests.fixtures import with_base_fixtures
from mycouch.tests.helpers import (
    DATABASE_CONFIG, prepare_database, auth_user, send_call)


class ActivityTestCase(unittest.TestCase):

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

    @with_base_fixtures
    def test_activity(self):
        # AUTHENTICATION here
        logged_user = auth_user(self.app, 'angelo', 'ciao')
        self.assertIsNotNone(logged_user)
        token = logged_user.get('token')

        today = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0)

        # message failure(s) here
        # 1. invalid status
        request = {
            'city_id': 1,
            'location': 'A location',
            'title': 'Activity name',
            'description': 'Activity description',
            'scheduled_from': today - timedelta(days=3, hours=19),
            'scheduled_until': today + timedelta(days=3, hours=22),
        }
        resp = send_call(self.app, 'post', '/activities',
                         request, token=token)
        self.assertEquals(resp.status[:3], '400')

        # 2. invalid city
        request = {
            'city_id': 3353335,  # non existing city
            'location': 'A location',
            'title': 'Activity name',
            'description': 'Activity description',
            'scheduled_from': today + timedelta(days=3, hours=19),
            'scheduled_until': today + timedelta(days=3, hours=22),
        }
        resp = send_call(self.app, 'post', '/activities',
                         request, token=token)
        self.assertEquals(resp.status[:3], '400')

        # 3. missing name
        request = {
            'city_id': 3353335,  # non existing city
            'location': 'A location',
            'description': 'Activity description',
            'scheduled_from': today + timedelta(days=3, hours=19),
            'scheduled_until': today + timedelta(days=3, hours=22),
        }
        resp = send_call(self.app, 'post', '/activities',
                         request, token=token)
        self.assertEquals(resp.status[:3], '400')

        # 4. valid - success
        request = {
            'city_id': 1,  # Berlin
            'location': 'A location',
            'title': 'Activity name',
            'description': 'Activity description',
            'scheduled_from': today + timedelta(days=3, hours=19),
            'scheduled_until': today + timedelta(days=3, hours=22),
        }
        resp = send_call(self.app, 'post', '/activities',
                         request, token=token)
        resp_data = json_loads(resp.data)
        self.assertEquals(resp.status[:3], '200')
        self.assertTrue(all(v == resp_data[k] for k, v in request.iteritems()))

        # fetching all activities - token not needed
        resp = send_call(self.app, 'get', '/activities')
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertTrue(isinstance(resp_data, list))
        self.assertEquals(len(resp_data), 1)
        this_one = resp_data[0]
        this_one_id = resp_data[0].get('id')
        self.assertTrue(this_one_id > 0)
        self.assertTrue(all(v == this_one[k] for k, v in request.iteritems()))

        attending_count = this_one.get('attending_count')
        self.assertTrue(isinstance(attending_count, dict))
        self.assertTrue(all(
            k in attending_count for k in ('yes', 'no', 'maybe')))
        self.assertEquals(attending_count['yes'], 1)
        self.assertEquals(attending_count['maybe'], 0)
        self.assertEquals(attending_count['no'], 0)

    def tearDown(self):
        db.session.close()

if __name__ == '__main__':
    unittest.main()
