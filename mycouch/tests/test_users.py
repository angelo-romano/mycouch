import os
import os.path
import simplejson
import sys
import unittest

cur_dir = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.append(cur_dir)

from flask.ext.sqlalchemy import SQLAlchemy
from mycouch import app, db
from mycouch.tests.helpers import DATABASE_CONFIG, prepare_database


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
        data = {
            'username': 'angelo',
            'password': 'ciao',
            'first_name': 'Angelo',
            'last_name': 'Romano',
            'email': 'angelo.romano@gmail.com',
        }
        data2 = {
            'username': 'angelo1',
            'password': 'ciao1',
            'first_name': 'Angelo1',
            'last_name': 'Romano1',
            'email': 'angelo.romano1@gmail.com',
        }
        # CREATING ACCOUNT 1
        resp = self.app.post('/users', 
            content_type='application/json',
            data=simplejson.dumps(data))
        resp_data = simplejson.loads(resp.data)
        self.assertTrue(all(data[key] == resp_data[key]
                            for key in data.iterkeys()
                            if key != 'password'))
        self.assertTrue(resp_data['id'] > 0)
        # CREATING ACCOUNT 2
        resp = self.app.post('/users', 
            content_type='application/json',
            data=simplejson.dumps(data2))
        resp_data2 = simplejson.loads(resp.data)
        self.assertTrue(all(data2[key] == resp_data2[key]
                            for key in data.iterkeys()
                            if key != 'password'))
        self.assertTrue(resp_data['id'] > 0)
        # GET EXPLICIT USER - AUTH FAILURE
        resp = self.app.get('/users/%s' % resp_data['id'], 
            content_type='application/json',
            data=simplejson.dumps(data))
        self.assertEquals(resp.status[:3], '401')
        # AUTHENTICATION COMES HERE
        resp = self.app.post('/auth',
            content_type='application/json',
            data=simplejson.dumps({'username': data['username'],
                                   'password': data['password'] + 'no'}))
        self.assertEquals(resp.status[:3], '401')

        resp = self.app.post('/auth',
            content_type='application/json',
            data=simplejson.dumps({'username': data['username'],
                                   'password': data['password']}))
        self.assertEquals(resp.status[:3], '200')
        # GET EXPLICIT USER - NOW WORKS
        resp = self.app.get('/users/%s' % resp_data['id'], 
            content_type='application/json')
        self.assertEquals(resp.status[:3], '200')
        self.assertTrue(all(data[key] == resp_data[key]
                            for key in data.iterkeys()
                            if key != 'password'))
        # UNAUTHORIZED
        resp = self.app.get('/users/%s' % resp_data2['id'], 
            content_type='application/json')
        self.assertEquals(resp.status[:3], '401')


    def tearDown(self):
        #cur = self.db_conn.cursor()
        #cur.execute('DROP DATABASE %s;' % DATABASE_CONFIG['dbname'])
        pass

if __name__ == '__main__':
    unittest.main()
