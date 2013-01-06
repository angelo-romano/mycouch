"""
Custom JSON serialization module, providing support for types who are not
natively recognized by `simplejson` (e.g., datetime objects or geometries).
"""
import re
import simplejson
from datetime import date, time, datetime

from mycouch import db


class ExtendedJSONEncoder(simplejson.JSONEncoder):
    def default(self, val):
        if isinstance(val, datetime):
            return val.strftime('%Y-%m-%dT%H:%M:%S')
        elif isinstance(val, date):
            return val.strftime('%Y-%m-%d')
        elif isinstance(val, time):
            return val.strftime('%H:%M:%S')
        elif hasattr(val, 'kml'):
            return {'_geo': val.coords(db.session)}
        return super(ExtendedJSONEncoder, self).default(val)


class ExtendedJSONDecoder(simplejson.JSONDecoder):

    def __init__(self, *args, **kwargs):
        kwargs['object_hook'] = self.parse_dict
        return super(ExtendedJSONDecoder, self).__init__(*args, **kwargs)

    @staticmethod
    def parse_dict(obj):
        """Parses a dict"""
        DATETIME_REGEX = re.compile(r'^\d{4}\-\d{2}\-\d{2}T\d{2}:\d{2}:\d{2}$')
        TIME_REGEX = re.compile(r'^\d{2}:\d{2}:\d{2}$')
        DATE_REGEX = re.compile(r'^\d{4}\-\d{2}\-\d{2}$')

        for key, val in obj.iteritems():
            if isinstance(val, basestring):
                if DATETIME_REGEX.match(val):
                    obj[key] = datetime.strptime(val, '%Y-%m-%dT%H:%M:%S')
                elif DATE_REGEX.match(val):
                    obj[key] = datetime.strptime(val, '%Y-%m-%d').date()
                elif TIME_REGEX.match(val):
                    obj[key] = datetime.strptime(val, '%H:%M:%S').time()
        return obj


def json_dumps(obj, indent=None):
    return simplejson.dumps(obj, cls=ExtendedJSONEncoder, use_decimal=True,
                            indent=indent)


def json_loads(obj):
    return simplejson.loads(obj, cls=ExtendedJSONDecoder, use_decimal=True)
