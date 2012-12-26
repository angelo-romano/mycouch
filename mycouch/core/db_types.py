from sqlalchemy import event
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import TypeDecorator, VARCHAR, Unicode
import json


class JSONType(TypeDecorator):
    "Represents an immutable structure as a json-encoded string."

    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class StateType(TypeDecorator):
    """
    Represents a state type with potential transitions.
    Transition dicts are in the form:
    {"state_from": ["state_to", "state_to"]*}

    Unspecified states are automatically considered as final ones.
    """

    impl = Unicode
    """
    @staticmethod
    def _before_attach_handler(session, instance):
        print 'session'
        print session
        print 'instance'
        print instance
        import pdb; pdb.set_trace()
    """
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
        """
        import pdb; pdb.set_trace()
        event.listen(self.metadata, 'before_attach', self._before_attach_handler)
        """

    def _evaluate_transition(self, value1, value2):
        if not self._transition_dict:  # no dict, all transitions allowed
            return True
        if (value1 in self._transition_dict and
                value2 in self._transition_dict[value1]):
            return True
        return False

    """
    def bind_processor(self, dialect):
        def process(value):
            if value in self._choices:
                return value
            else:
                raise ValueError('Invalid choice')
        return process
    """
