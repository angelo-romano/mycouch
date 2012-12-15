import os
import os.path
import simplejson
import sys
import unittest
from decimal import Decimal

cur_dir = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.append(cur_dir)

from flask.ext.sqlalchemy import SQLAlchemy
from mycouch import app, db
from mycouch.tests.helpers import DATABASE_CONFIG, prepare_database


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

    def test_this(self):
        data = {
            'rating': Decimal('1.41199860'),
            'name': 'Hobro',
            'country_code': 'DEN',
            'latitude': Decimal('56.6332999999999984'),
            'timezone': 1,
            'slug': 'hobro',
            'longitude': Decimal('9.8000000000000007'),
            'wikiname': 'Hobro',
            'type': 'city'}
        # CREATING CITY [ERROR]
        data['type'] = 'not_a_city'
        resp = self.app.post('/locations/%s' % data['type'],
            content_type='application/json',
            data=simplejson.dumps(data, use_decimal=True))
        self.assertEquals(resp.status[:3], '400')
        # CREATING CITY [ERROR]
        data['type'] = 'city'
        resp = self.app.post('/locations/%s' % data['type'],
            content_type='application/json',
            data=simplejson.dumps(data, use_decimal=True))
        self.assertEquals(resp.status[:3], '200')
        resp_data = simplejson.loads(resp.data, use_decimal=True)
        print '1', data
        print '2', resp_data
        #self.assertTrue(all(data[key] == resp_data[key]
        #                    for key in data.iterkeys()))
        self.assertTrue(resp_data['id'] > 0)
        # GET EXPLICIT LOCATION - NOW WORKS
        resp = self.app.get('/locations/%s/%s' % (
            resp_data['type'], resp_data['id']),
            content_type='application/json')
        self.assertEquals(resp.status[:3], '200')
        resp_data = simplejson.loads(resp.data, use_decimal=True)
        #self.assertTrue(all(data[key] == resp_data[key]
        #                    for key in data.iterkeys()))
        # GET EXPLICIT LOCATION - NOW WORKS
        resp = self.app.get('/locations/%s/%s' % (
            resp_data['type'], resp_data['id'] + 100000),
            content_type='application/json')
        self.assertEquals(resp.status[:3], '404')


    def tearDown(self):
        #cur = self.db_conn.cursor()
        #cur.execute('DROP DATABASE %s;' % DATABASE_CONFIG['dbname'])
        pass

if __name__ == '__main__':
    unittest.main()
