"""
Module destined to contain string-related helper functions shared throughout
the whole dowant application.
"""
import re


def force_unicode(s):
    """
    Forces a string cast to its unicode equivalent (using UTF-8).

    Returns:
    a unicode-type string.
    """
    return (s.decode('utf8')
            if isinstance(s, str)
            else unicode(s))


def force_str(s):
    """
    Forces a string cast to its str equivalent (using UTF-8). It is the
    str-based equivalent of <force_unicode>.

    Returns:
    a str-type string.
    """
    return (s.encode('utf8')
            if isinstance(s, unicode)
            else str(s))

