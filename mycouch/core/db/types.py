import collections
import simplejson

from sqlalchemy.inspection import inspect
from sqlalchemy.types import (
    TypeDecorator, VARCHAR, Unicode, UserDefinedType)
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


class HStoreType(UserDefinedType):
    """The ``hstore`` type that stores a dictionary.  It can take an any
    instance of :class:`collections.Mapping`.

    It can be extended to store other types than string e.g.::

        class IntegerBooleanHstore(Hstore):
            '''The ``hstore`` type for integer keys and boolean values.'''

            def map_bind_key(self, key):
                if key is not None:
                    return unicode(key)

            def map_bind_value(self, value):
                if value is not None:
                    return u't' if value else u'f'

            def map_result_key(self, key):
                if key is not None:
                    return int(key)

            def map_result_value(self, value):
                if value is not None:
                    return value == u't'

    :param value_nullable: to prevent ``None`` (``NULL``) for dictionary
                           values, set it ``True``. default is ``False``
    :type value_nullable: :class:`bool`

    """

    def __init__(self, value_nullable=True):
        self.value_nullable = bool(value_nullable)

    def map_bind_key(self, key):
        """The mapping function that is used for binding keys.  The default
        implementation is just a string identity function.

        :param key: a key object to bind
        :returns: a mapped key string
        :rtype: :class:`unicode`

        """
        if key is None:
            return
        if not isinstance(key, basestring):
            raise TypeError('hstore key must be a string, not ' + repr(key))
        return unicode(key)

    def map_bind_value(self, value):
        """The mapping function that is used for binding values.
        The default implementation is just a string identity function.

        :param value: a value to bind
        :returns: a mapped value string
        :rtype: :class:`unicode`

        """
        if value is None:
            return
        if not isinstance(value, basestring):
            raise TypeError('hstore value must be a string, not ' +
                            repr(value))
        return unicode(value)

    def map_result_key(self, key):
        """The mapping function that is used for resulting keys.  The default
        implementation is just an identity function.

        :param key: a raw key of the result
        :type key: :class:`unicode`
        :returns: a mapped key object

        """
        return key

    def map_result_value(self, value):
        """The mapping function that is used for resulting values.
        The default implementation is just an identity function.

        :param key: a raw value of the result
        :type key: :class:`unicode`
        :returns: a mapped value

        """
        return value

    def get_col_spec(self):
        return 'hstore'

    def is_mutable(self):
        return True

    def compare_values(self, x, y):
        x = None if x is None else dict(x)
        y = None if y is None else dict(y)
        return x == y

    def copy_value(self, value):
        if value is not None:
            return dict(value)

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return
            if not isinstance(value, collections.Mapping):
                raise TypeError('expected a collections.Mapping object, not '
                                + repr(value))
            items = getattr(value, 'iteritems', value.items)()
            map_bind_key = self.map_bind_key

            def map_key(key):
                if key is None:
                    raise TypeError('hstore key cannot be None')
                return map_bind_key(key)

            if self.value_nullable:
                map_value = self.map_bind_value
            else:
                map_bind_value = self.map_bind_value

                def map_value(value):
                    if value is None:
                        raise TypeError('hstore value cannot be None')
                    return map_bind_value(value)

            return dict((map_key(k), map_value(v)) for k, v in items)
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            map_key = self.map_result_key
            map_value = self.map_result_value
            return dict((map_key(k), map_value(v))
                        for k, v in value.iteritems())
        return process

# make JSONType a mutable type
MutationDict.associate_with(HStoreType)


class StateType(TypeDecorator):
    """
    Represents a state type with potential transitions.
    Transition dicts are in the form:
    {"state_from": ["state_to", "state_to"]*}

    Unspecified states are automatically considered as final ones.
    """

    impl = HStoreType

    def __init__(self, choices=None, transitions=None, *args, **kwargs):
        super(StateType, self).__init__(*args, **kwargs)
        if transitions and not choices and isinstance(transitions, dict):
            choices = set(transitions.keys() + sum(transitions.values(), []))
        if not isinstance(choices, (list, set, tuple, frozenset)):
            raise TypeError('Invalid choices type')
        if not choices:
            raise ValueError('Choices cannot be empty')
        self._choices = set(choices)
        self._transition_dict = transitions

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
            return {'success': value, '1': simplejson.dumps([value, ''])}
        return value


def make_transition(instance, fieldname, new_value, author_id=None):
    type_instance = inspect(instance.__class__).columns[fieldname].type
    curval = getattr(instance, fieldname) or MutationDict()
    curval_current = curval.get('current')

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
