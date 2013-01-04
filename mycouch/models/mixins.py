from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.inspection import inspect
from datetime import datetime
from geoalchemy import GeometryColumn, Point
from sqlalchemy import (
    Column, Integer, Unicode, UnicodeText, DateTime, Float, ForeignKey,
    and_)
from sqlalchemy.orm import relationship
from mycouch import db
from mycouch.core.auth_sa import get_user_class
from mycouch.core.db import Base
from mycouch.core.db.types import (
    JSONType, HStoreType, SlugType, StateType, make_transition)
from mycouch.core.utils import serialize_db_value, slugify


AuthUserBase = get_user_class(Base)


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

    def _make_slug(self, force_unique=True):
        # slug handling
        slug_fields = [(k, v.type._field)
                       for (k, v) in inspect(self.__class__).columns.items()
                       if isinstance(v.type, SlugType)]
        for (slug_field, name_field) in slug_fields:
            slug_field_val = getattr(self, slug_field)
            if slug_field_val:
                continue

            name_field_val = getattr(self, name_field, '')
            slug_base = slugify(name_field_val)
            slug = slug_base
            if self.__class__.query.filter_by(
                    **{slug_field: slug}).first():
                with_auto_slug = [long(o.slug.split('--')[-1])
                                  for o in self.__class__.query.filter(
                                      getattr(self.__class__, slug_field).like(
                                          '%s--%%' % slug_base)).all()]
                if with_auto_slug:
                    max_id = max(with_auto_slug)
                else:
                    max_id = 0
                slug = '%s--%s' % (slug_base, max_id + 1)
            setattr(self, slug_field, slug)

    def force_serialize(self, fields):
        if fields:
            fields_to_add = (
                list(fields)
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
            if isinstance(attr_val, Base):
                attr_val = attr_val.serialized

            resp[attr] = serialize_db_value(attr_val)

        return resp

    def save(self, commit=False):
        self._make_slug()
        db.session.add(self)
        if commit:
            self.commit()

    def commit(self):
        return db.session.commit()

    def populate_from_json(self, json_dict):
        for (key, val) in json_dict.iteritems():
            if isinstance(val, dict) and '_geo' in val:
                v = tuple(val['_geo'])
                setattr(self, key, 'POINT(%s %s)' % v)
            else:
                setattr(self, key, val)


class ConnectionMixin(object):
    """
    The connection model mixin.
    """
    id = declared_attr(lambda self: Column(Integer, primary_key=True))

    description = declared_attr(lambda self: Column(
        Unicode(128), nullable=False))
    text = declared_attr(lambda self: Column(UnicodeText, nullable=False))
    user_from_id = declared_attr(lambda self: Column(
        Integer, ForeignKey('auth_user.id'), nullable=True))
    user_from = declared_attr(lambda self: relationship(
        'User', cascade='all, delete',
        single_parent=True,
        primaryjoin=('foreign(%s.c.user_from_id)==auth_user.c.id'
                     % self.__tablename__)))
    user_to_id = declared_attr(lambda self: Column(
        Integer, ForeignKey('auth_user.id'), nullable=True))
    user_to = declared_attr(lambda self: relationship(
        'User', cascade='all, delete',
        single_parent=True,
        primaryjoin=('foreign(%s.c.user_to_id)==auth_user.c.id'
                     % self.__tablename__)))

    sent_on = declared_attr(lambda self: Column(
        DateTime, nullable=False, default=datetime.utcnow))

    type = declared_attr(lambda self: Column(Unicode(24), nullable=False))
    type_status = declared_attr(lambda self: Column(
        StateType(transitions=self.__state_transitions__), nullable=False))

    flags = declared_attr(lambda self: Column(JSONType, nullable=False))


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
    flags = declared_attr(lambda self: Column(JSONType, nullable=True))
    sender_id = declared_attr(lambda self: Column(
        Integer, ForeignKey('auth_user.id'), nullable=False))
    sender = declared_attr(lambda self: relationship(
        'User', single_parent=True, cascade='all, delete'))
    reply_to_id = declared_attr(lambda self: Column(
        Integer, ForeignKey('%s.id' % self.__tablename__), nullable=True))
    reply_to = declared_attr(lambda self: relationship(
        self, cascade='all, delete',
        single_parent=True,
        primaryjoin='remote({0}.c.id)==foreign({0}.c.reply_to_id)'.format(
            self.__tablename__)))

    def change_flags(self, add=None, remove=None):
        pass

    @property
    def recipient_list(self):
        from mycouch.models import User
        return User.query.filter(User.id.in_(self.recipient_list_ids))

    @classmethod
    def get_incoming(cls, user, additional_filters=None):
        query = cls.query.filter(and_(
            cls.__notification_class__.message_id == cls.id,
            cls.user_id == user.id))
        if additional_filters:
            if isinstance(additional_filters, dict):
                query = query.filter_by(**additional_filters)
            else:
                query = query.filter(*additional_filters)
        return query.all()

    @classmethod
    def get_outgoing(cls, user, additional_filters=None):
        query = cls.query.filter(cls.sender_id == user.id)
        if additional_filters:
            if isinstance(additional_filters, dict):
                query = query.filter_by(**additional_filters)
            else:
                query = query.filter(*additional_filters)
        return query.all()

    def send_to(self, *user_list):
        """
        Message send operation.
        """
        notification_class = self.__notification_class__
        self.recipient_list_ids = [o.id for o in user_list]
        self.save()
        for user in user_list:
            notification = notification_class(
                user=user,
                message=self)
            notification.save()
        if self.reply_to_id:
            reply_notification = notification_class.query.filter(
                id=self.reply_to_id).first()
            make_transition(reply_notification, 'status', 'replied')
            reply_notification.save()
        self.commit()

    def serialized_func(self, user):
        return self.serialized


class MessagingNotificationMixin(object):
    """
    The messaging notification model mixin.
    """
    id = declared_attr(lambda self: Column(Integer, primary_key=True))
    user_id = declared_attr(lambda self: Column(
        Integer, ForeignKey('auth_user.id'), nullable=False))
    user = declared_attr(lambda self: relationship(
        'User', single_parent=True, cascade='all, delete'))
    message_id = declared_attr(lambda self: Column(
        Integer, ForeignKey(self.__message_class__.id), nullable=False))
    message = declared_attr(lambda self: relationship(
        self.__message_class__, single_parent=True, cascade='all, delete'))
    status = declared_attr(lambda self: Column(
        StateType(transitions=self.__state_transitions__),
        nullable=False, default='unread'))

    @declared_attr
    def __state_transitions__(self):
        return {
            'unread': ['read', 'replied', 'deleted', 'archived'],
            'read': ['deleted', 'archived', 'replied'],
            'archived': ['deleted'],
        }

    def change_status(self, new_status):
        if (self.__state_transitions__ and
                new_status not in self.__state_transitions__[self.status]):
            raise ValueError('Invalid state transition.')
        make_transition(self, 'status', new_status)
        self.save()


class AreaMixin(object):
    """
    The area mixin (e.g., region, country).
    """
    id = declared_attr(lambda self: Column(Integer, primary_key=True))
    name = declared_attr(lambda self: Column(Unicode(128), nullable=False))
    wikiname = declared_attr(lambda self: Column(Unicode(90)))
    slug = declared_attr(lambda self: Column(
        SlugType(field='name'), nullable=False))
    rating = declared_attr(lambda self: Column(Float, default=0))
    code = declared_attr(lambda self: Column(Unicode(5), nullable=True))

    capital_city_id = declared_attr(lambda self: Column(
        Integer, nullable=True))  # TODO - foreignkey here causes circular dep
    capital_city = declared_attr(lambda self: relationship(
        'City',
        primaryjoin=('foreign(%s.c.capital_city_id)==geo_city.c.id'
                     % self.__tablename__)))


class LocalityMixin(object):
    """
    The location mixin.
    """
    __do_not_serialize__ = ('coordinates',)
    __force_serialize__ = ('country_code', 'latitude', 'longitude')

    id = declared_attr(lambda self: Column(Integer, primary_key=True))
    name = declared_attr(lambda self: Column(Unicode(128), nullable=False))
    wikiname = declared_attr(lambda self: Column(Unicode(90)))
    slug = declared_attr(lambda self: Column(
        SlugType(field='name'), nullable=False))
    rating = declared_attr(lambda self: Column(Float, default=0))

    coordinates = declared_attr(lambda self: GeometryColumn(
        Point(2), nullable=False))
    timezone = declared_attr(lambda self: Column(Integer, default=0))
    country_id = declared_attr(lambda self: Column(
        Integer, ForeignKey('geo_country.id'), nullable=False))
    country = declared_attr(lambda self: relationship(
        'Country',
        primaryjoin=('foreign(%s.c.country_id)==geo_country.c.id'
                     % self.__tablename__)))

    additional_data = declared_attr(lambda self: Column(
        HStoreType, nullable=False, default={}))

    @property
    def latitude(self):
        return db.session.scalar(self.coordinates.x)

    @property
    def longitude(self):
        return db.session.scalar(self.coordinates.y)

    @property
    def country_code(self):
        return self.country.code
