from flask import Flask, g
from flaskext.auth import Auth
from flaskext.babel import Babel
from flask.ext.sqlalchemy import SQLAlchemy

from mycouch import settings
from mycouch.api.base import register_api
from mycouch.core import setup_routing

# setup application
app = Flask('mycouch')
app.config.from_object(settings)

# setup database
db = SQLAlchemy(app)
babel = Babel(app)
auth = Auth(app)

from mycouch import models
# register application views and blueprints
from mycouch.urls import routes
setup_routing(app, routes)

# register API
#api_manager = get_api_manager(app, db)
#register_api(api_manager)
register_api(app)

# Babel
@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    user = getattr(g, 'user', None)
    if user is not None:
        return user.locale
    # otherwise try to guess the language from the user accept
    # header the browser transmits.  We support de/fr/en in this
    # example.  The best match wins.
    return request.accept_languages.best_match([
        'en', 'it', 'fr', 'es', 'nl', 'de'])

@babel.timezoneselector
def get_timezone():
    user = getattr(g, 'user', None)
    if user is not None:
        return user.timezone

print app.url_map
