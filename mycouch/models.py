from sqlalchemy.ext.declarative import declared_attr

from mycouch import db
from datetime import datetime
from decimal import Decimal
from geoalchemy import (
    GeometryColumn, GeometryDDL, Point, WKTSpatialElement)
from sqlalchemy import (
    Column, Integer, Unicode, UnicodeText, DateTime,
    UniqueConstraint, ForeignKey, Float)

from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship, backref

from mycouch.core.db_types import JSONType
from mycouch.core.auth_sa import get_user_class
from mycouch.core.utils import slugify, get_country_name, serialize_db_value


AuthUserBase = get_user_class(db.Model)


class AutoInitMixin(object):
    """
    Mixin for populating models columns automatically (no need
    to define an __init__ method) and set the default value if any.
    Also sets the model id and __tablename__ automatically.
    """
    @declared_attr
    def __do_not_serialize__(self):
        return ()

    @declared_attr
    def __force_serialize__(self):
        return ()

    id = db.Column(db.Integer, primary_key=True)

    def __init__(self, *args, **kwargs):
        for attr in (a for a in self._sa_class_manager.keys()):
            attr_obj = getattr(self, attr)
            print attr, attr_obj
            if isinstance(attr_obj, db.Column):
                set_val, val = False, None
                if attr in kwargs:
                    set_val, val = True, kwargs[attr]
                else:
                    if hasattr(attr_obj, 'default'):
                        if callable(attr_obj.default):
                            set_val, val = True, attr_obj.default()
                        else:
                            set_val, val = True, attr_obj.default
                if set_val:
                    if isinstance(attr_obj, GeometryColumn):
                        val = WKTSpatialElement('POINT(%s)' % ' '.join(val))
                    setattr(self, attr, val)

    @property
    def serialized(self):
        resp = {}
        fields = set(a for a in self._sa_class_manager.keys()
                     if not a.startswith('_')
                     and a not in self.__do_not_serialize__)
        fields.update(set(self.__force_serialize__))
        for attr in fields:
            attr_val = getattr(self, attr)
            if isinstance(attr_val, db.Model):
                attr_val = attr_val.serialized
            resp[attr] = serialize_db_value(attr_val)
        return resp

    def save(self, commit=False):
        db.session.add(self)
        if commit:
            self.commit()

    def commit(self):
        return db.session.commit()


class User(AuthUserBase, AutoInitMixin):
    __tablename__ = 'auth_user'
    __api_resource__ = 'users'
    __do_not_serialize__ = (
        'password', 'salt', 'role', 'modified', 'city_id')
    __force_serialize__ = (
        'country', 'country_code')

    id = db.Column(db.Integer, primary_key=True)

    first_name = Column(Unicode(64), nullable=True)
    last_name = Column(Unicode(64), nullable=True)
    email = Column(Unicode(64), nullable=False)
    city_id = Column(Integer, ForeignKey('geo_city.id'))
    websites = Column(JSONType, nullable=True)

    city = relationship('City')

    @property
    def country_code(self):
        return self.city.country_code if self.city else None

    @property
    def country(self):
        return self.city.country if self.city else None

def declared(name, c):
    def fn(self):
        return c
    fn.__name__ = name
    return declared_attr(fn)


class LocationMixin(object):
    __do_not_serialize__ = ('coordinates',)
    __force_serialize__ = (
        'country', 'country_code', 'latitude', 'longitude')

    id = declared('id', Column(Integer, primary_key=True))
    name = declared('name', Column(Unicode(128), nullable=False))
    country_code = declared('country_code', Column(Unicode(5), nullable=False))
    coordinates = declared('coordinates', GeometryColumn(Point(2), nullable=False))
    wikiname = declared('wikiname', Column(Unicode(90)))
    timezone = declared('timezone', Column(Integer, default=0))
    slug = declared('slug', Column(Unicode(64), nullable=False))
    rating = declared('rating', Column(Float, default=0))

    @property
    def country(self):
        return get_country_name(self.country_code)

    @property
    def latitude(self):
        return db.session.scalar(self.coordinates.x)

    @property
    def longitude(self):
        return db.session.scalar(self.coordinates.y)

class City(db.Model, LocationMixin, AutoInitMixin):
    __tablename__ = 'geo_city'
    __api_resource__ = 'cities'

    id = Column(Integer, primary_key=True)

UniqueConstraint(City.name, City.country_code)

# activates the Geo DDL for City table
GeometryDDL(City.__table__)
