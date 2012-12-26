from datetime import datetime
from mycouch import db
from geoalchemy import (
    GeometryDDL, GeometryColumn, Point)

from sqlalchemy import (
    Column, Integer, Unicode, UnicodeText, DateTime,
    UniqueConstraint, ForeignKey)

#from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship, backref

from mycouch.core.db_types import JSONType, StateType
from mycouch.core.auth_sa import get_user_class
from mycouch.core.utils import slugify
from mycouch.models.mixins import (
    AutoInitMixin, LocalityMixin, MessagingMixin,
    MessagingNotificationMixin, ConnectionMixin)


AuthUserBase = get_user_class(db.Model)


class User(AuthUserBase, AutoInitMixin):
    """
    The main user model.
    """
    __tablename__ = 'auth_user'
    __do_not_serialize__ = (
        'password', 'salt', 'role', 'modified', 'city')
    __force_serialize__ = (
        'country', 'country_code')

    id = Column(Integer, primary_key=True)

    first_name = Column(Unicode(64), nullable=True)
    last_name = Column(Unicode(64), nullable=True)
    email = Column(Unicode(64), nullable=False)
    city_id = Column(Integer, ForeignKey('geo_city.id'), nullable=True)
    websites = Column(JSONType, nullable=True)

    city = relationship('City')

    @property
    def country_code(self):
        return self.city.country_code if self.city else None

    @property
    def country(self):
        return self.city.country if self.city else None


class City(db.Model, LocalityMixin, AutoInitMixin):
    """
    Main city model.
    """
    __tablename__ = 'geo_city'


# (slug, country_code) are unique as a couple
UniqueConstraint(City.slug, City.country_code)

# activates the Geo DDL for City table
GeometryDDL(City.__table__)


class MinorLocality(db.Model, LocalityMixin, AutoInitMixin):
    """
    Model representing a "minor locality" (not an official city).
    """
    __tablename__ = 'geo_minorlocality'

    # choices neighbourhood, village, hamlet, town, suburb, etc.
    locality_type = Column(Unicode(20), nullable=False)

    city_id = Column(Integer, ForeignKey(City.id), nullable=True)
    city = relationship(City)


# activates the Geo DDL for City table
GeometryDDL(MinorLocality.__table__)


class Activity(db.Model, AutoInitMixin):
    """
    The activity model.
    """
    __tablename__ = 'activity_activity'
    __do_not_serialize__ = (
        'creator_id',)
    __force_serialize__ = (
        'attending_count',)

    id = Column(Integer, primary_key=True)

    creator_id = Column(Integer, ForeignKey(User.id), nullable=False)
    creator = relationship(User)

    title = Column(Unicode(128), nullable=False)
    description = Column(UnicodeText, nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    scheduled_from = Column(DateTime, nullable=False)
    scheduled_until = Column(DateTime, nullable=True)

    location = Column(Unicode(128), nullable=False)
    # TODO - should be nullable=False
    location_coordinates = GeometryColumn(Point(2), nullable=True)

    locality_id = Column(Integer, ForeignKey(City.id), nullable=False)
    locality = relationship(City)

    def set_user_rsvp(self, user, rsvp_status):
        activity_rsvp = ActivityRSVP.query.filter_by(
            activity_id=self.id,
            user_id=user.id).first()
        if not activity_rsvp:
            activity_rsvp = ActivityRSVP(
                user_id=user.id,
                activity_id=self.id,
                rsvp_status=rsvp_status)
        else:
            activity_rsvp.rsvp_status = rsvp_status
        activity_rsvp.save(commit=True)

    @property
    def attending_count(self):
        base_query = ActivityRSVP.query.filter_by(activity_id=self.id)
        return dict((k, base_query.filter_by(rsvp_status=k).count())
                    for k in ActivityRSVP.RSVP_STATUSES)

# activates the Geo DDL for Activity table
GeometryDDL(Activity.__table__)


class ActivityRSVP(db.Model, AutoInitMixin):
    """
    The activity RSVP model.
    """
    __tablename__ = 'activity_activityrsvp'
    __do_not_serialize__ = (
        'id',)

    RSVP_STATUSES = frozenset(['yes', 'no', 'maybe'])

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey(Activity.id), nullable=False)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)

    rsvp_status = Column(Unicode(16), nullable=False, index=True)
    comment = Column(Unicode(90), nullable=True)

    activity = relationship(Activity)
    user = relationship(User)

# (user, activity) are unique as a couple - a user can RSVP only once
UniqueConstraint(ActivityRSVP.user_id, ActivityRSVP.activity_id)


class PrivateMessage(db.Model, MessagingMixin, AutoInitMixin):
    """
    The private message model.
    """
    __tablename__ = 'message_privatemessage'


class PrivateMessageNotification(db.Model, MessagingNotificationMixin,
                                 AutoInitMixin):
    """
    The private message notification model.
    """
    __tablename__ = 'message_privatemessagenotification'
    __message_class__ = PrivateMessage


class HospitalityRequest(db.Model, MessagingMixin, AutoInitMixin):
    """
    The hospitality request model.
    """
    __tablename__ = 'message_hospitalityrequest'
    __state_transitions__ = {
        'unread': ['accepted', 'refused', 'maybe'],
        'accepted': ['refused', 'maybe'],
        'maybe': ['accepted', 'refused'],
    }
    status = Column(StateType(transitions=__state_transitions__),
                    default='unread', nullable=False)


class HospitalityRequestNotification(db.Model, MessagingNotificationMixin,
                                     AutoInitMixin):
    """
    The hospitality request notification model.
    """
    __tablename__ = 'message_hospitalityrequestnotification'
    __message_class__ = HospitalityRequest


class FriendshipConnection(db.Model, ConnectionMixin, AutoInitMixin):
    """
    The friendship connection model.
    """
    __tablename__ = 'connection_friendship'
    __state_transitions__ = {
        'pending': ['accepted', 'refused'],
        'accepted': ['removed'],
    }

    def serializer_func(self, user):
        resp = self.serialized
        return resp


class Reference(db.Model, ConnectionMixin, AutoInitMixin):
    """
    The reference model.
    """
    __tablename__ = 'connection_reference'
    __state_transitions__ = {
        'positive': [],
        'neutral': [],
        'negative': [],
    }

    def serializer_func(self, user):
        resp = self.serialized
        return resp


class Group(db.Model, AutoInitMixin):
    """
    The group model.
    """
    __tablename__ = 'group_group'

    id = Column(Integer, primary_key=True)
    slug = Column(Unicode(64), nullable=False, unique=True)

    parent_group_id = Column(Integer, ForeignKey(id), nullable=True)
    parent_group = relationship(Group)

    title = Column(Unicode(64), nullable=False)
    description = Column(UnicodeText, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    city_id = Column(Integer, ForeignKey(City.id), nullable=True)
    minorlocality_id = Column(
        Integer, ForeignKey(MinorLocality.id), nullable=True)

    root_group_posts = relationship(
        'GroupPost',
        primaryjoin=and_('Group.id==GroupPost.group_id',
                         'GroupPost.reply_to_id==None'))

# (slug, country_code) are unique as a couple
UniqueConstraint(Group.title, Group.parent_group_id)


class GroupPost(db.Model, MessagingMixin, AutoInitMixin):
    """
    The group post model.
    """
    __tablename__ = 'group_grouppost'

    group_id = Column(Integer, ForeignKey(Group.id), nullable=False)
    group = relationship(Group, backref='group_posts')
