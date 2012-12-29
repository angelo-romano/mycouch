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

    @with_fixtures('city', 'user')
    def test_this(self):
        group = {
            'title': 'Main Berlin Group',
            'description': 'Description',
            'city_id': 335,
        }
        subgroup = {
            'title': 'Main Berlin Subgroup',
            'description': 'Description',
            'city_id': 335,
        }
        # AUTHENTICATION here
        logged_user = auth_user(self.app, 'angelo', 'ciao')
        self.assertIsNotNone(logged_user)
        token = logged_user.get('token')

        # group creation
        resp = send_call(self.app, 'post', '/groups',
                         group, token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        # subgroup creation
        subgroup['parent_group_id'] = resp_data.get('id')
        resp = send_call(self.app, 'post', '/groups',
                         subgroup, token=token)
        self.assertEquals(resp.status[:3], '200')

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
