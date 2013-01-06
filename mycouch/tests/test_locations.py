import os
import os.path
import sys
import unittest
from decimal import Decimal

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

    @with_base_fixtures
    def test_this(self):
        data = {
            'rating': Decimal('1.41199860'),
            'name': 'Hobro',
            'country_id': 11,  # Germany
            'latitude': Decimal('56.6332999999999984'),
            'timezone': 1,
            'slug': 'hobro',
            'longitude': Decimal('9.8000000000000007'),
            'wikiname': 'Hobro',
            'type': 'cities'}
        data2 = {
            'rating': Decimal('1.80019736'),
            'name': 'Hoddesdon',
            'country_id': 11,  # Germany
            'latitude': Decimal('51.7500000000000000'),
            'timezone': 0,
            'type': 'cities',
            'slug': 'hoddesdon',
            'longitude': Decimal('0E-16'),
            'wikiname': 'Hoddesdon'}
        # CREATING CITY [ERROR]
        logged_user = auth_user(self.app, 'angelo', 'ciao')
        self.assertIsNotNone(logged_user)
        token = logged_user.get('token')

        data['type'] = 'not_a_cities'
        resp = send_call(self.app, 'post', '/locations/%s' % data['type'],
                         data, token=token)
        self.assertEquals(resp.status[:3], '400')
        # CREATING CITY [ERROR]
        data['type'] = 'cities'
        resp = send_call(self.app, 'post', '/locations/%s' % data['type'],
                         data, token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        self.assertTrue(resp_data['id'] > 0)
        # GET EXPLICIT LOCATION - NOW WORKS
        resp = send_call(self.app, 'get', '/locations/%s/%s' % (
            resp_data['type'], resp_data['id']), token=token)
        self.assertEquals(resp.status[:3], '200')
        resp_data = json_loads(resp.data)
        # GET EXPLICIT LOCATION - NOW WORKS
        resp = send_call(self.app, 'get', '/locations/%s/%s' % (
            resp_data['type'], resp_data['id'] + 100000), token=token)
        self.assertEquals(resp.status[:3], '404')

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
