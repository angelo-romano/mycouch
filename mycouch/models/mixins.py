# 2012.12.23 21:09:00 CET
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.inspection import inspect
from datetime import datetime
from geoalchemy import GeometryColumn, Point, WKTSpatialElement
from sqlalchemy import (
    Column, Integer, Unicode, UnicodeText, DateTime, Float, ForeignKey)
from sqlalchemy.orm import relationship, remote, foreign
from mycouch import db
from mycouch.core.auth_sa import get_user_class
from mycouch.core.db_types import JSONType
from mycouch.core.utils import get_country_name, serialize_db_value


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

    def __init__(self, *args, **kwargs):
        keys = inspect(self.__class__)
        keys = (
            [o.key for o in keys.relationships] +
            [o.name for o in keys.columns])
        for attr in keys:
            attr_obj = getattr(self, attr)
            print attr,
            print attr_obj
            if isinstance(attr_obj, db.Column):
                (set_val, val,) = (False, None)
                if attr in kwargs:
                    (set_val, val,) = (True, kwargs[attr])
                elif hasattr(attr_obj, 'default'):
                    if callable(attr_obj.default):
                        (set_val, val,) = (True, attr_obj.default())
                    else:
                        (set_val, val,) = (True, attr_obj.default)
                if set_val:
                    if isinstance(attr_obj, GeometryColumn):
                        val = WKTSpatialElement('POINT(%s)' % ' '.join(val))
                    setattr(self, attr, val)

    def force_serialize(self, fields):
        if fields:
            fields_to_add = (list(fields)
                             if isinstance(fields, (list, set, frozenset, tuple))
                             else [fields])
            self.__force_serialize__ = tuple(
                list(self.__force_serialize__) + fields_to_add)

    @property
    def serialized(self):
        resp = {}
        fields = set((o.name for o in inspect(self.__class__).columns))
        fields = set((a for a in fields if not a.startswith('_')
                      if a not in self.__do_not_serialize__))
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


class MessagingMixin(object):
    """
    The messaging model mixin.
    """
    id = declared_attr(lambda self: Column(Integer, primary_key=True))

    subject = declared_attr(lambda self: Column(Unicode(128), nullable=False))
    text = declared_attr(lambda self: Column(UnicodeText, nullable=False))
    recipient_list_ids = declared_attr(lambda self: Column(
        JSONType, nullable=False))
    type = declared_attr(lambda self: Column(Unicode(24), nullable=False))
    sent_on = declared_attr(lambda self: Column(
        DateTime, nullable=False, default=datetime.utcnow))
    flags = declared_attr(lambda self: Column(JSONType, nullable=False))
    sender_id = declared_attr(lambda self: Column(
        Integer, ForeignKey('auth_user.id'), nullable=False))
    sender = declared_attr(lambda self: relationship('User'))
    reply_to_id = declared_attr(lambda self: Column(
        Integer, ForeignKey('%s.id' % self.__tablename__), nullable=True))
    reply_to = declared_attr(lambda self: relationship(
        self,
        primaryjoin='remote({0}.c.id)==foreign({0}.c.reply_to_id)'.format(
            self.__tablename__)))

    @property
    def recipient_list(self):
        from mycouch.models import User
        return User.query.filter(User.id.in_(self.recipient_list_ids))


class ConnectionMixin(object):
    """
    The connection model mixin.
    """
    id = declared_attr(lambda self: Column(Integer, primary_key=True))

    description = declared_attr(lambda self: Column(Unicode(128), nullable=False))
    text = declared_attr(lambda self: Column(UnicodeText, nullable=False))
    user_from_id = declared_attr(lambda self: Column(
        Integer, ForeignKey('auth_user.id'), nullable=True))
    user_from = declared_attr(lambda self: relationship(
        'User',
        primaryjoin='foreign(%s.c.user_from_id)==auth_user.c.id' %
            self.__tablename__))
    user_to_id = declared_attr(lambda self: Column(
        Integer, ForeignKey('auth_user.id'), nullable=True))
    user_to = declared_attr(lambda self: relationship(
        'User',
        primaryjoin='foreign(%s.c.user_to_id)==auth_user.c.id' %
            self.__tablename__))

    sent_on = declared_attr(lambda self: Column(
        DateTime, nullable=False, default=datetime.utcnow))

    type = declared_attr(lambda self: Column(Unicode(24), nullable=False))
    type_status = declared_attr(lambda self: Column(Unicode(24), nullable=False))

    flags = declared_attr(lambda self: Column(JSONType, nullable=False))


class MessagingNotificationMixin(object):
    """
    The messaging notification model mixin.
    """
    id = declared_attr(lambda self: Column(Integer, primary_key=True))
    user_id = declared_attr(lambda self: Column(
        Integer, ForeignKey('auth_user.id'), nullable=False))
    user = declared_attr(lambda self: relationship('User'))
    message_id = declared_attr(lambda self: Column(
        Integer, ForeignKey(self.__message_class__.id), nullable=False))
    message = declared_attr(lambda self: relationship(self.__message_class__))
    status = declared_attr(lambda self: Column(
        Unicode(24), nullable=False, default='unread'))


class LocationMixin(object):
    """
    The location mixin.
    """
    __do_not_serialize__ = ('coordinates',)
    __force_serialize__ = ('country', 'country_code', 'latitude', 'longitude')

    id = declared_attr(lambda self: Column(Integer, primary_key=True))
    name = declared_attr(lambda self: Column(Unicode(128), nullable=False))
    country_code = declared_attr(lambda self: Column(
        Unicode(5), nullable=False))
    coordinates = declared_attr(lambda self: GeometryColumn(
        Point(2), nullable=False))
    wikiname = declared_attr(lambda self: Column(Unicode(90)))
    timezone = declared_attr(lambda self: Column(Integer, default=0))
    slug = declared_attr(lambda self: Column(Unicode(64), nullable=False))
    rating = declared_attr(lambda self: Column(Float, default=0))

    @property
    def country(self):
        return get_country_name(self.country_code)

    @property
    def latitude(self):
        return db.session.scalar(self.coordinates.x)

    @property
    def longitude(self):
        return db.session.scalar(self.coordinates.y)
