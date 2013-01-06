"""
Custom database types for SQLAlchemy usage.
"""
import collections
import simplejson

from sqlalchemy.inspection import inspect
from sqlalchemy.types import (
    TypeDecorator, VARCHAR, Unicode, UserDefinedType)
from sqlalchemy.dialects.postgresql import HSTORE
from sqlalchemy.ext.mutable import Mutable


class MutationDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutationDict."

        if not isinstance(value, MutationDict):
            if isinstance(value, dict):
                return MutationDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."

        dict.__delitem__(self, key)
        self.changed()


class StateMutationDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to StateMutationDict."

        if not isinstance(value, StateMutationDict):
            if isinstance(value, dict):
                return StateMutationDict(value)
            elif isinstance(value, basestring):
                return StateMutationDict({
                    'current': value,
                    '1': simplejson.dumps([value, ''])})

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."

        dict.__delitem__(self, key)
        self.changed()



class JSONType(TypeDecorator):
    "Represents an immutable structure as a json-encoded string."

    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = simplejson.dumps(value, use_decimal=True)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = simplejson.loads(value, use_decimal=True)
        return value


class SlugType(TypeDecorator):
    impl = Unicode

    def __init__(self, *args, **kwargs):
        if 'field' in kwargs:
            field = kwargs.pop('field')
        super(SlugType, self).__init__(*args, **kwargs)
        self._field = field


HStoreType = HSTORE
MutationDict.associate_with(HStoreType)


class StateType(TypeDecorator):
    """
    Represents a state type with potential transitions.
    Transition dicts are in the form:
    {"state_from": ["state_to", "state_to"]*}

    Unspecified states are automatically considered as final ones.
    """

    impl = HSTORE

    def __init__(self, choices=None, transitions=None, *args, **kwargs):
        super(StateType, self).__init__(*args, **kwargs)
        if transitions and not choices and isinstance(transitions, dict):
            choices = set(transitions.keys() + sum(transitions.values(), []))

        if not choices:
            raise ValueError('Choices cannot be empty')
        if not isinstance(choices, (list, set, tuple, frozenset)):
            raise TypeError('Invalid choices type')

        self._choices = set(choices) if choices else set()
        self._transition_dict = transitions

    def is_mutable(self):
        return True

    def evaluate_transition(self, value1, value2):
        if not self._transition_dict:  # no dict, all transitions allowed
            return True
        if (value1 in self._transition_dict and
                value2 in self._transition_dict[value1]):
            return True
        else:
            if value2 not in self._choices:
                raise StateValueError
            else:
                raise StateTransitionError

    def process_bind_param(self, value, dialect):
        if not isinstance(value, dict):
            return {'current': value, '1': simplejson.dumps([value, ''])}
        return value

# make StateType a mutable type
StateMutationDict.associate_with(StateType)


def make_transition(instance, fieldname, new_value, author_id=None):
    type_instance = inspect(instance.__class__).columns[fieldname].type
    curval = StateMutationDict(getattr(instance, fieldname)) or StateMutationDict()
    curval_current = curval.get('current')

    if new_value == curval_current:
        # no need to update
        return

    # will raise exception in case of failure
    if not curval_current or type_instance.evaluate_transition(
            curval_current, new_value):
        # new value storage
        # hstore will be in the form {'1': '["V", "1"]', 'current': '"1"'}
        max_key = max([0] + [int(k) for k in curval.iterkeys() if k.isdigit()])
        newval_entry = simplejson.dumps(
            [new_value, str(author_id) if author_id else ''])
        curval[str(max_key + 1)] = newval_entry
        curval['current'] = new_value
        setattr(instance, fieldname, curval)


class StateTransitionError(ValueError):
    pass


class StateValueError(ValueError):
    pass
