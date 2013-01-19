"""
The root module containing all SQLALchemy model definitions.
"""
from datetime import datetime, date
from geoalchemy import (
    GeometryDDL, GeometryColumn, Point)

from sqlalchemy import (
    Column, Integer, Unicode, UnicodeText, Date, DateTime, Boolean, Enum,
    UniqueConstraint, ForeignKey, or_)

#from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship, backref
from mycouch.core.auth_sa import get_user_class
from mycouch.core.db import Base
from mycouch.core.db.types import JSONType, StateType, SlugType
from mycouch.core.utils import serialize_db_value, force_str, force_unicode
from mycouch.models.mixins import (
    AutoInitMixin, AreaMixin, LocalityMixin, MessagingMixin,
    MessagingNotificationMixin, ConnectionMixin)


AuthUserBase = get_user_class(Base)


GENDER_CHOICES = {  # ISO/IEC 5218
    '0': u'Not known',
    '1': u'Female',
    '2': u'Male',
    '9': u'Not applicable',
}
"""
The ISO/IEC 5218 convention for gender choices. Used in the <User> model
definition.
"""

HOST_CHOICES = {
    'yes': 'Yes (most of the time)',
    'no': 'No, never',
    'maybe': 'Depends on the person',
    'sometimes': 'Occasionally',
    'coffee': 'I can\'t, but I am fine to help/meet anyways!',
}

class User(AuthUserBase, AutoInitMixin):
    """
    The main user model.
    """
    __tablename__ = 'auth_user'
    __do_not_serialize__ = (
        'password', 'salt', 'role', 'modified', 'city', 'country')
    __force_serialize__ = (
        'country_code', 'details', 'age',
        'n_refs', 'n_friends', 'keywords', 'has_details')
    __searchable__ = True

    id = Column(Integer, primary_key=True)

    first_name = Column(Unicode(64), nullable=True)
    last_name = Column(Unicode(64), nullable=True)
    email = Column(Unicode(64), nullable=False)
    gender = Column(Enum(*GENDER_CHOICES.keys(), name='gender_enum'),
                    nullable=False)
    birth_date = Column(Date, nullable=False)

    city_id = Column(Integer, ForeignKey('geo_city.id'), nullable=True)
    city = relationship('City')

    can_host = Column(
        Enum(*HOST_CHOICES.keys(), name='can_host_enum'),
        default='no', nullable=False)

    @property
    def gender_description(self):
        """
        The full gender description (e.g., 'Male', 'Female').

        :rtype: str
        """
        return GENDER_CHOICES[self.gender]

    @property
    def country_code(self):
        """
        The country code for the current user's nationality. Country codes
        follow the ISO 3166-1 alpha 3 definition.

        :rtype: str
        """
        return self.city.country_code if self.city else None

    @property
    def country(self):
        """
        The country object for this specific user.

        :rtype: <Country>
        """
        return self.city.country if self.city else None

    @property
    def age(self):
        """
        The user's current age.

        :rtype: int
        """
        today = date.today()

        try:
            # raised when birth date is February 29
            # and the current year is not a leap year
            birthday = self.birth_date.replace(year=today.year)
        except ValueError:
            birthday = self.birth_date.replace(
                year=today.year, day=self.birth_date.day - 1)

        if birthday > today:
            return today.year - self.birth_date.year - 1
        else:
            return today.year - self.birth_date.year

    @property
    def n_refs(self):
        return Reference.query.filter_by(user_to_id=self.id).count()

    @property
    def n_friends(self):
        return FriendshipConnection.query.filter(or_(
            FriendshipConnection.user_from_id == self.id,
            FriendshipConnection.user_to_id == self.id)).count()

    @property
    def has_details(self):
        return bool(self.details and any((
            self.details.sections, self.details.profile_details)))

    @property
    def keywords(self):
        # TO BE IMPLEMENTED
        return []


class UserProfileDetails(Base, AutoInitMixin):
    """
    User profile details for a specific account (e.g., profile sections,
    websites of reference, additional profile details).
    """
    __tablename__ = 'auth_userprofiledetails'
    __do_not_serialize__ = (
        'id', 'user_id')

    id = Column(Integer, primary_key=True)
    websites = Column(JSONType, nullable=True)
    sections = Column(JSONType, nullable=True)
    profile_details = Column(JSONType, nullable=True)

    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    user = relationship(User, backref=backref('details', uselist=False))


class City(Base, LocalityMixin, AutoInitMixin):
    """
    Main city model.
    """
    __tablename__ = 'geo_city'
    __searchable__ = True

    def __str__(self):
        return force_str(self.name)

    def __repr__(self):
        return '<City%s%s>' % (
            '' if not self.id else ' #%s' % self.id,
            '' if not self.name else ': %s' % force_str(self.name))


# (slug, country_code) are unique as a couple
UniqueConstraint(City.slug, City.country_id)

# activates the Geo DDL for City table
GeometryDDL(City.__table__)


class MinorLocality(Base, LocalityMixin, AutoInitMixin):
    """
    Model representing a "minor locality" (not an official city, can be a
    neighbourhood or a smaller village which is administratively part of a
    larger municipality).
    """
    __tablename__ = 'geo_minorlocality'
    __searchable__ = True

    # choices neighbourhood, village, hamlet, town, suburb, etc.
    locality_type = Column(Unicode(20), nullable=False)

    city_id = Column(Integer, ForeignKey(City.id), nullable=True)
    city = relationship(City)


# activates the Geo DDL for City table
GeometryDDL(MinorLocality.__table__)


class Country(Base, AreaMixin, AutoInitMixin):
    """
    Main country model.
    """
    __tablename__ = 'geo_country'
    __do_not_serialize__ = ('languages', 'wikiname')
    __searchable__ = True

    languages = Column(JSONType, nullable=True)


class RegionalArea(Base, AreaMixin, AutoInitMixin):
    """
    Main regional area model (i.e., a official/unofficial subnational entity).
    """
    __tablename__ = 'geo_regionalarea'
    __searchable__ = True

    parent_area_id = Column(
        Integer, ForeignKey('%s.id' % __tablename__), nullable=True)
    parent_area = relationship(
        'RegionalArea',
        cascade='all, delete', single_parent=True,
        primaryjoin='remote({0}.c.id)==foreign({0}.c.parent_area_id)'.format(
            __tablename__))

    country_id = Column(Integer, ForeignKey(Country.id), nullable=False)
    country = relationship(Country)


class Activity(Base, AutoInitMixin):
    """
    The activity model.
    """
    __tablename__ = 'activity_activity'
    __do_not_serialize__ = (
        'creator_id',)
    __force_serialize__ = (
        'attending_count',)
    __searchable__ = True

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

    city_id = Column(Integer, ForeignKey(City.id), nullable=False)
    city = relationship(City)

    def set_user_rsvp(self, user, rsvp_status):
        """
        Registers the specific user to a given RSVP status.

        :param user: the user object.
        :type user: <User>
        :param rsvp_status: the RSVP status (one of 'yes', 'no', 'maybe').
        :type rsvp_status: str
        """
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
        """
        A dictionary structure containing the number of registered users
        per RSVP status, in the form

            {"yes": X, "maybe": Y, "no": Z}

        :rtype: dict
        """
        base_query = ActivityRSVP.query.filter_by(activity_id=self.id)
        return dict((k, base_query.filter_by(rsvp_status=k).count())
                    for k in ActivityRSVP.RSVP_STATUSES)

# activates the Geo DDL for Activity table
GeometryDDL(Activity.__table__)


class ActivityRSVP(Base, AutoInitMixin):
    """
    The activity RSVP model.
    """
    __tablename__ = 'activity_activityrsvp'
    __do_not_serialize__ = (
        'id',)

    RSVP_STATUSES = frozenset(['yes', 'no', 'maybe'])

    id = Column(Integer, primary_key=True)

    activity_id = Column(Integer, ForeignKey(Activity.id), nullable=False)
    activity = relationship(Activity)

    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    user = relationship(User)

    rsvp_status = Column(Unicode(16), nullable=False, index=True)
    comment = Column(Unicode(90), nullable=True)


# (user, activity) are unique as a couple - a user can RSVP only once
UniqueConstraint(ActivityRSVP.user_id, ActivityRSVP.activity_id)


class PrivateMessage(Base, MessagingMixin, AutoInitMixin):
    """
    The private message model.
    """
    __tablename__ = 'message_privatemessage'

    __mapper_args__ = {
        'polymorphic_on': 'type',
        'polymorphic_identity': 'private_message'}

    @classmethod
    def validate_values(cls, values):
        # mandatory field check
        mandatory_errors, type_errors, other_errors = (
            cls._check_mandatory_fields(
                values, ('subject', 'text',
                         'sender_id', 'recipient_list_ids')),
            [], [])

        # other field error check - reply_to_id
        if values.get('reply_to_id'):
            parent_msg = cls.query.filter_by(id=values['reply_to_id']).first()

            if not parent_msg:
                # cannot reply to the original message - not found
                other_errors.append(
                    'Original message mentioned by '
                    '"reply_to_id" not found.')
            elif (values.get('sender_id') and
                    values.get('sender_id') not in parent_msg.recipient_list_ids):
                other_errors.append(
                    '"reply_to_id" does not reference to a repliable message.')

        return cls._build_validation_dict(
            mandatory_errors, type_errors, other_errors)


class PrivateMessageNotification(Base, MessagingNotificationMixin,
                                 AutoInitMixin):
    """
    The private message notification model.
    """
    __tablename__ = 'message_privatemessagenotification'
    __message_class__ = PrivateMessage

PrivateMessage.__notification_class__ = PrivateMessageNotification


class HospitalityRequest(Base, MessagingMixin, AutoInitMixin):
    """
    The hospitality request model.
    """
    __tablename__ = 'message_hospitalityrequest'
    __state_transitions__ = {
        'unread': ['accepted', 'refused', 'maybe', 'canceled'],
        'accepted': ['refused', 'maybe', 'canceled'],
        'maybe': ['accepted', 'refused', 'canceled'],
        'canceled': ['accepted', 'maybe'],
    }
    date_from = Column(Date, nullable=False)
    date_to = Column(Date, nullable=False)
    additional_details = Column(JSONType, nullable=True)

    status = Column(StateType(transitions=__state_transitions__),
                    default='unread', nullable=False)

    @classmethod
    def validate_values(cls, values):
        # mandatory field check
        mandatory_errors, type_errors, other_errors = (
            cls._check_mandatory_fields(
                values, ('date_from', 'date_to', 'subject', 'text',
                         'sender_id', 'recipient_list_ids')),
            [], [])

        # other field error check - reply_to_id
        if values.get('reply_to_id'):
            parent_msg = cls.query.filter_by(id=values['reply_to_id']).first()

            if not parent_msg:
                # cannot reply to the original message - not found
                other_errors.append(
                    'Original message mentioned by '
                    '"reply_to_id" not found.')
            elif (values.get('sender_id') and
                    values.get('sender_id') not in parent_msg.recipient_list_ids):
                other_errors.append(
                    '"reply_to_id" does not reference to a repliable message.')

        # other field error check - date_from, date_to
        date_from, date_to = values.get('date_from'), values.get('date_to')
        recipient_list_ids = values.get('recipient_list_ids')
        if date_from and date_from < date.today():
            other_errors.append(
                'Value for "date_from" cannot be in the past.')
        if date_to:
            if date_to < date.today():
                other_errors.append(
                    'Value for "date_to" cannot be in the past.')
            if date_from and date_to < date_from:
                other_errors.append(
                    'Value for "date_to" must be greater or equal '
                    'than "date_from".')
        if (recipient_list_ids and isinstance(recipient_list_ids, list) and 
                len(recipient_list_ids) != 1):
            other_errors.append('Must be exactly one element in "recipient_list_ids".')

        return cls._build_validation_dict(
            mandatory_errors, type_errors, other_errors)

    def change_status(self, new_status):
        """
        Changes the status of this hospitality request to a new one.

        :param new_status: the new status (one of 'accepted', 'refused',
                           'maybe', 'canceled').
        :type new_status: str
        """
        if (self.__state_transitions__ and
                new_status not in self.__state_transitions__[self.status]):
            raise ValueError('Invalid state transition.')
        self.status = new_status
        self.save()

    __mapper_args__ = {
        'polymorphic_on': 'type',
        'polymorphic_identity': 'hospitality_request'}


class HospitalityRequestNotification(Base, MessagingNotificationMixin,
                                     AutoInitMixin):
    """
    The hospitality request notification model.
    """
    __tablename__ = 'message_hospitalityrequestnotification'
    __message_class__ = HospitalityRequest

HospitalityRequest.__notification_class__ = HospitalityRequestNotification


class FriendshipConnection(Base, ConnectionMixin, AutoInitMixin):
    """
    The friendship connection model.
    """
    __tablename__ = 'connection_friendship'
    __state_transitions__ = {
        'pending': ['accepted', 'refused'],
        'accepted': ['removed'],
    }

    __do_not_serialize__ = (
        'user_from_id', 'user_to_id')

    FRIENDSHIP_LEVEL_CHOICES = {
        'acquaintance': 'Acquaintance',
        'friend': 'Friend',
        'relative': 'Relative',
        'partner': 'Partner',
        'good_friend': 'Good friend',
        'best_friend': 'Best friend',
    }

    friendship_level = Column(
        Enum(*FRIENDSHIP_LEVEL_CHOICES.keys(), name='friendship_level_enum'),
        default='friend', nullable=False)

    @classmethod
    def validate_friendship_level(cls, level):
        """
        Checks if a specific friendship level is compliant with the allowed
        alternatives.

        :param level: the friendship level to be validated.
        :type level: str

        :returns: True if it is valid, False otherwise.
        :rtype: bool
        """
        return (level in cls.FRIENDSHIP_LEVEL_CHOICES)

    @property
    def friendship_level_description(self):
        """
        The full description of the friendship level for this specific
        connection object (e.g., 'Acquaintance', 'Friend', etc.)

        :rtype: str
        """
        return self.FRIENDSHIP_LEVEL_CHOICES.get(self.friendship_level)

    def serializer_func(self, user):
        """
        Given the currently logged user, returns the appropriate serialization.

        :param user: the current user.
        :type user: <User>

        :returns: the JSON-friendly representation of this connection for API
                  purposes.
        :rtype: dict
        """
        resp = self.serialized
        resp['user_id'] = serialize_db_value(
            self.user_from_id
            if self.user_to_id == user.id else self.user_to_id)

        return resp

    __mapper_args__ = {
        'polymorphic_on': 'type',
        'polymorphic_identity': 'friendship'}


class Reference(Base, ConnectionMixin, AutoInitMixin):
    """
    The reference model.
    """
    __tablename__ = 'connection_reference'
    __state_transitions__ = {
        'positive': [],
        'neutral': [],
        'negative': [],
    }

    __do_not_serialize__ = (
        'user_from_id', 'user_to_id', 'type_status', 'description')

    @classmethod
    def validate_reference_type(cls, reftype):
        """
        Checks if a specific reference level is compliant with the allowed
        alternatives.

        :param level: the reference level to be validated.
        :type level: str

        :returns: True if it is valid, False otherwise.
        :rtype: bool
        """
        return (reftype in cls.__state_transitions__)

    def serializer_func(self, user):
        """
        Given the currently logged user, returns the appropriate serialization.

        :param user: the current user.
        :type user: <User>

        :returns: the JSON-friendly representation of this reference for API
                  purposes.
        :rtype: dict
        """
        resp = self.serialized
        update_dict = (
            ('user_id', (self.user_from_id
                         if self.user_to_id == user.id else self.user_to_id)),
            ('reference_type', self.type_status))

        resp.update(dict((k, serialize_db_value(v))
                         for (k, v) in update_dict))
        return resp

    __mapper_args__ = {
        'polymorphic_on': 'type',
        'polymorphic_identity': 'reference'}


class Group(Base, AutoInitMixin):
    """
    The group model.
    """
    __tablename__ = 'group_group'
    __searchable__ = True

    id = Column(Integer, primary_key=True)
    slug = Column(SlugType(field='title'), nullable=False, unique=True)

    creator_id = Column(Integer, ForeignKey(User.id), nullable=True)
    creator = relationship(User)

    parent_group_id = Column(Integer, ForeignKey(id), nullable=True)
    parent_group = relationship(
        'Group',
        primaryjoin='remote({0}.c.id)==foreign({0}.c.parent_group_id)'.format(
            __tablename__))

    title = Column(Unicode(64), nullable=False)
    description = Column(UnicodeText, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    city_id = Column(Integer, ForeignKey(City.id), nullable=True)
    minorlocality_id = Column(
        Integer, ForeignKey(MinorLocality.id), nullable=True)

    root_group_posts = relationship(
        'GroupPost',
        primaryjoin=(
            'and_(Group.id==GroupPost.group_id,'
            'GroupPost.reply_to_id==None)'))

# (slug, country_code) are unique as a couple
UniqueConstraint(Group.title, Group.parent_group_id)


class GroupPost(Base, MessagingMixin, AutoInitMixin):
    """
    The group post model.
    """
    __tablename__ = 'group_grouppost'

    group_id = Column(Integer, ForeignKey(Group.id), nullable=False)
    group = relationship(Group, backref='group_posts')
