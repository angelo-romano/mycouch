"""
Module to provide plug-and-play authentication support for SQLAlchemy.
"""
import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, and_
from flaskext.auth import AuthUser
from flask import g
from mycouch.api.auth import MemcachedAuthHandler, get_current_token


def get_user_class(declarative_base):
    """
    Factory function to create an SQLAlchemy User model with a declarative.
    base (for example db.Model from the Flask-SQLAlchemy extension).
    """
    class User(declarative_base, AuthUser):
        """
        Implementation of User for SQLAlchemy.
        """
        __abstract__ = True

        id = Column(Integer, primary_key=True)
        username = Column(String(80), unique=True, nullable=False)
        password = Column(String(120), nullable=False)
        salt = Column(String(80))
        role = Column(String(80))
        created = Column(DateTime(), default=datetime.datetime.utcnow)
        modified = Column(DateTime())
        is_active = Column(Boolean, default=True, nullable=False)

        def __init__(self, *args, **kwargs):
            super(User, self).__init__(*args, **kwargs)
            password = kwargs.get('password')
            if password is not None and not self.id:
                self.created = datetime.datetime.utcnow()
                # Initialize and encrypt password before first save.
                self.set_and_encrypt_password(password)

        def __getstate__(self):
            return {
                'id': self.id,
                'username': self.username,
                'role': self.role,
                'created': self.created,
                'modified': self.modified,
            }

        def authenticate(self, password):
            resp = super(User, self).authenticate(password)
            if resp:
                auth_handler = MemcachedAuthHandler()
                resp = auth_handler.set(self)
                g.auth_token = resp
            return resp

        @classmethod
        def load_current_user(cls, apply_timeout=True):
            auth_handler = MemcachedAuthHandler()
            data = auth_handler.get(
                getattr(g, 'auth_token', None) or get_current_token())
            if not data:
                return None
            return cls.query.filter(and_(
                cls.username == data['username'],
                cls.is_active)).first()

    return User
