import os.path
import sys
import unittest
from datetime import date, time, datetime
from decimal import Decimal

cur_dir = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.append(cur_dir)

from flask.ext.sqlalchemy import SQLAlchemy
from mycouch import app, db
from mycouch.core.serializers import json_dumps, json_loads


class JSONTestCase(unittest.TestCase):

    def test_this(self):
        data = {
            'decimal': Decimal('1.41199860'),
            'string': 'Hobro',
            'integer': 1,
            'date': date(2012, 11, 11),
            'time': time(15, 30),
            'datetime': datetime(2012, 12, 10, 16, 43),
        }
        base_one = json_dumps(data)
        base_two = json_loads(base_one)
        self.assertEquals(data, base_two)


if __name__ == '__main__':
    unittest.main()
