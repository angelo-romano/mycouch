"""
The root database handling module.
"""
from sqlalchemy.inspection import inspect
from geoalchemy import GeometryColumn, WKTSpatialElement, Geometry

from mycouch import db
from mycouch.core.db.types import StateType, make_transition


def hack_declarative_base():
    """
    Hacks the full declarative base.
    """
    Base = db.Model

    def __init__(self, *args, **kwargs):
        """
        The new constructor.
        """
        inspector = inspect(self.__class__)
        keys = (
            [(False, o.key) for o in inspector.relationships] +
            [(True, o.name) for o in inspector.columns])
        for is_column, attr in keys:
            if is_column:
                # column processing
                col = inspector.columns[attr]
                (set_val, val) = (False, None)
                if attr in kwargs:
                    (set_val, val) = (True, kwargs[attr])
                if set_val and val is not None:
                    if (isinstance(col.type, Geometry) and
                            not isinstance(val, WKTSpatialElement)):
                        val = WKTSpatialElement('POINT(%s)' % ' '.join(val))
                    if isinstance(col.type, StateType):
                        make_transition(self, attr, val)
                    else:
                        setattr(self, attr, val)
            else:
                # relationship
                if attr in kwargs:
                    setattr(self, attr, kwargs[attr])

    Base.__init__ = __init__
    return Base

Base = hack_declarative_base()
