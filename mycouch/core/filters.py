import re
from jinja2 import Markup

_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')


def nl2br(value):
    result = u'\n\n'.join(u'<p>{0}</p>'.format(p.replace('\n', '<br />\n'))
                          for p in _paragraph_re.split(value))
    result = Markup(result)
    return result
