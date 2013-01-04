import re

from datetime import date, time, datetime
from flaskext.babel import gettext as _
from mycouch import db
from unidecode import unidecode


_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')


COUNTRY_CODE_LIST = {
    'ALB': _('Albania'),
    'AND': _('Andorra'),
    'ARM': _('Armenia'),
    'AUT': _('Austria'),
    'AZE': _('Azerbaijan'),
    'BLR': _('Belarus'),
    'BEL': _('Belgium'),
    'BIH': _('Bosnia and Herzegovina'),
    'BUL': _('Bulgaria'),
    'CRO': _('Croatia'),
    'CYP': _('Cyprus'),
    'CZE': _('Czech Republic'),
    'DEN': _('Denmark'),
    'EST': _('Estonia'),
    'FRO': _('Faroe Islands'),
    'FIN': _('Finland'),
    'FRA': _('France'),
    'GEO': _('Georgia'),
    'GER': _('Germany'),
    'GIB': _('Gibraltar'),
    'GRE': _('Greece'),
    'GLD': _('Greenland'),
    'HUN': _('Hungary'),
    'ISL': _('Iceland'),
    'IRL': _('Ireland'),
    'ISR': _('Israel'),
    'ITA': _('Italy'),
    'KOS': _('Kosovo'),
    'LAT': _('Latvia'),
    'LIE': _('Liechtenstein'),
    'LTU': _('Lithuania'),
    'LUX': _('Luxembourg'),
    'MLT': _('Malta'),
    'MDA': _('Moldova'),
    'MON': _('Monaco'),
    'MNE': _('Montenegro'),
    'NED': _('Netherlands'),
    'NOR': _('Norway'),
    'POL': _('Poland'),
    'POR': _('Portugal'),
    'MKD': _('Republic of Macedonia'),
    'ROU': _('Romania'),
    'RUS': _('Russia'),
    'SMR': _('San Marino'),
    'SRB': _('Serbia'),
    'SVK': _('Slovakia'),
    'SLO': _('Slovenia'),
    'ESP': _('Spain'),
    'SWE': _('Sweden'),
    'SUI': _('Switzerland'),
    'TUR': _('Turkey'),
    'UKR': _('Ukraine'),
    'GBR': _('United Kingdom'),
    'VAT': _('Vatican City'),
}


def is_state_dict(val):
    if not isinstance(val, dict):
        return False
    if 'current' not in val:
        return False

    keys = [k for k in val.iterkeys() if k != 'current']
    return all(o.isdigit() for o in keys)


def serialize_db_value(val):
    if isinstance(val, datetime):
        return val.strftime('%Y-%m-%dT%H:%M:%S')
    elif isinstance(val, date):
        return val.strftime('%Y-%m-%d')
    elif isinstance(val, time):
        return val.strftime('%H:%M:%S')
    elif is_state_dict(val):
        return val.get('current')
    elif hasattr(val, 'kml'):
        return (val.coords(db.session))
    return val


def datetime_from_json(val):
    return datetime.strptime(val, '%Y-%m-%dT%H:%M:%S')


def get_country_name(country_code):
    return COUNTRY_CODE_LIST[country_code]


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


def slugify(text, delim=u'-'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    text = unidecode(force_unicode(text))
    for word in _punct_re.split(text.lower()):
        word = unicode(word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))
